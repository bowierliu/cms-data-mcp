"""Bounded acquisition of one public CMS metadata record and fixed scalar count."""

import hashlib
import ipaddress
import json
import re
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from functools import partial
from typing import Any, TypeVar

import anyio
import httpx2
from pydantic import ValidationError

from cms_mcp.models import (
    MAX_RESPONSE_BYTES,
    CountObservation,
    CountResponseError,
    Provenance,
    SourceReference,
    count_request,
)

METADATA_URL = (
    "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/"
    "mj5m-pzi6?show-reference-ids"
)
COUNT_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0"
DICTIONARY_URL = (
    "https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/"
    "physician/DOC_Data_Dictionary.pdf"
)
LANDING_URL = "https://data.cms.gov/provider-data/dataset/mj5m-pzi6"
TOTAL_TIMEOUT_SECONDS = 30.0
SOCKET_TIMEOUT_SECONDS = 10.0
RETRY_DELAY_SECONDS = 0.25
MAX_RETRY_DELAY_SECONDS = 2.0
_T = TypeVar("_T")


class SourceError(ValueError):
    """Fixed code only; rejected bodies and exception chains must not escape."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_key")
        value[key] = item
    return value


def _reject_constant(_: str) -> None:
    raise ValueError("invalid_constant")


def _catalog_date(value: object) -> date | None:
    if value is None:
        return None
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("invalid_date")
    return date.fromisoformat(value)


def _parse_metadata(body: bytes, checked_at: datetime) -> SourceReference:
    try:
        metadata = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        if not isinstance(metadata, dict):
            raise ValueError("invalid_shape")
        if (
            metadata.get("identifier") != "mj5m-pzi6"
            or metadata.get("title") != "National Downloadable File"
            or metadata.get("accessLevel") != "public"
            or metadata.get("landingPage") != LANDING_URL
        ):
            raise ValueError("invalid_identity")
        publisher = metadata["publisher"]
        if (
            publisher["identifier"] != "4c1de1c4-f083-5877-8968-7ddc04756c49"
            or publisher["data"]["name"] != "Centers for Medicare & Medicaid Services (CMS)"
        ):
            raise ValueError("invalid_publisher")
        distributions = metadata["distribution"]
        if not isinstance(distributions, list) or len(distributions) != 1:
            raise ValueError("ambiguous_distribution")
        distribution = distributions[0]
        details = distribution["data"]
        if (
            details["mediaType"] != "text/csv"
            or details["describedBy"] != DICTIONARY_URL
            or details["describedByType"] != "application/pdf"
        ):
            raise ValueError("invalid_distribution")
        return SourceReference(
            distribution_id=distribution["identifier"],
            download_url=details["downloadURL"],
            catalog_released=_catalog_date(metadata.get("released")),
            catalog_modified=_catalog_date(metadata.get("modified")),
            metadata_hash=hashlib.sha256(body).hexdigest(),
            checked_at=checked_at,
            synthetic=False,
        )
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        pass
    raise SourceError("source_metadata_invalid")


class _PublicCMSTransport(httpx2.AsyncBaseTransport):
    """Pin a checked public IP while verifying TLS against the CMS hostname."""

    def __init__(self) -> None:
        self._inner = httpx2.AsyncHTTPTransport(verify=True, trust_env=False, retries=0)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        if (request.method, str(request.url)) not in (("GET", METADATA_URL), ("POST", COUNT_URL)):
            raise SourceError("source_scope_invalid")
        # A cancelled resolver must not hold up asyncio's default executor shutdown.
        # The OS lookup may finish in this abandoned daemon worker, without HTTP I/O.
        answers = await anyio.to_thread.run_sync(
            partial(socket.getaddrinfo, "data.cms.gov", 443, type=socket.SOCK_STREAM),
            abandon_on_cancel=True,
        )
        addresses = [str(answer[4][0]) for answer in answers]
        parsed = [ipaddress.ip_address(ip) for ip in addresses]
        if not parsed or any(not ip.is_global or ip.is_multicast for ip in parsed):
            raise SourceError("source_address_rejected")
        # Numeric connection target avoids a second, unchecked DNS resolution.
        # The documented SNI extension preserves certificate hostname verification.
        pinned = httpx2.Request(
            request.method,
            request.url.copy_with(host=addresses[0]),
            headers=request.headers,
            stream=request.stream,
            extensions=request.extensions | {"sni_hostname": "data.cms.gov"},
        )
        pinned.headers["host"] = "data.cms.gov"
        return await self._inner.handle_async_request(pinned)

    async def aclose(self) -> None:
        await self._inner.aclose()


def _retry_delay(value: str | None) -> float | None:
    """Never retry earlier than Retry-After; refuse waits above the small budget."""
    delay = RETRY_DELAY_SECONDS
    if value is not None:
        try:
            if re.fullmatch(r"\d+", value):
                delay = float(value)
            else:
                instant = parsedate_to_datetime(value)
                if instant.tzinfo is None:
                    return None
                delay = max(0.0, (instant - datetime.now(UTC)).total_seconds())
        except (ValueError, OverflowError, TypeError):
            return None
    return delay if 0 <= delay <= MAX_RETRY_DELAY_SECONDS else None


def _run_safely(operation: Callable[[], Awaitable[_T]]) -> _T:
    error = "source_unavailable"
    try:
        return anyio.run(operation)
    except SourceError as exc:
        error = str(exc)
    except (TimeoutError, httpx2.TimeoutException):
        error = "source_timeout"
    except Exception:
        pass
    # Leaving the handlers detaches potentially sensitive transport/parser contexts.
    raise SourceError(error)


class CMSClient:
    """Synchronous operations for a worker thread; no caller-controlled network scope."""

    def __init__(
        self,
        clock: Callable[[], datetime] = _utc_now,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._clock = clock
        self._transport = transport

    def metadata(self) -> SourceReference:
        """Verify catalog authority and capture current evidence; never fetch the CSV."""
        return _run_safely(self._metadata_operation)

    def retrieve(self, source: SourceReference) -> Provenance:
        """Revalidate source, execute exact fixed count, and reject metadata drift."""
        error = "source_scope_invalid"
        try:
            validated = SourceReference.model_validate(source)
            if not validated.synthetic:
                return _run_safely(partial(self._retrieve, validated))
            error = "live_source_required"
        except ValidationError:
            pass
        raise SourceError(error)

    async def _metadata_operation(self) -> SourceReference:
        with anyio.fail_after(TOTAL_TIMEOUT_SECONDS):
            async with self._client() as client:
                return await self._metadata(client)

    def _client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(
            transport=self._transport or _PublicCMSTransport(),
            follow_redirects=False,
            verify=True,
            trust_env=False,
            timeout=SOCKET_TIMEOUT_SECONDS,
            headers={"accept": "application/json", "accept-encoding": "identity"},
        )

    async def _metadata(self, client: httpx2.AsyncClient) -> SourceReference:
        body = await self._request(client, "GET", METADATA_URL)
        return _parse_metadata(body, self._clock())

    async def _retrieve(self, source: SourceReference) -> Provenance:
        with anyio.fail_after(TOTAL_TIMEOUT_SECONDS):
            async with self._client() as client:
                before = await self._metadata(client)
                self._consistent_source(source, before)
                if before.checked_at < source.checked_at:
                    raise SourceError("source_clock_invalid")
                body = await self._request(client, "POST", COUNT_URL)
                retrieved_at = self._clock()
                try:
                    observation = CountObservation.from_response(
                        body, source=source, retrieved_at=retrieved_at
                    )
                except (CountResponseError, ValidationError):
                    observation = None
                if observation is None:
                    raise SourceError("count_response_invalid")
                if observation.retrieved_at < before.checked_at:
                    raise SourceError("source_clock_invalid")
                after = await self._metadata(client)
                self._consistent_source(source, after)
                if after.checked_at < observation.retrieved_at:
                    raise SourceError("source_clock_invalid")
                try:
                    provenance = Provenance.from_observation(
                        observation, normalized_at=self._clock()
                    )
                    if provenance.lineage[0].executed_at >= after.checked_at:
                        return provenance
                except ValidationError:
                    pass
                raise SourceError("source_clock_invalid")

    @staticmethod
    def _consistent_source(expected: SourceReference, actual: SourceReference) -> None:
        if expected.model_dump(exclude={"checked_at"}) != actual.model_dump(exclude={"checked_at"}):
            raise SourceError("source_changed")

    async def _request(self, client: httpx2.AsyncClient, method: str, url: str) -> bytes:
        for attempt in range(2):
            delay: float | None = RETRY_DELAY_SECONDS
            failure = "source_unavailable"
            try:
                async with client.stream(
                    method, url, json=count_request() if method == "POST" else None
                ) as response:
                    if response.status_code in (429, 503):
                        delay = _retry_delay(response.headers.get("retry-after"))
                    elif response.status_code != 200:
                        raise SourceError("source_http_error")
                    else:
                        return await self._body(response)
            except httpx2.TimeoutException:
                failure = "source_timeout"
            # Transport failures other than timeouts are not retried.
            if attempt == 1 or delay is None:
                raise SourceError(failure)
            await anyio.sleep(delay)
        raise SourceError("source_unavailable")  # defensive; the loop always returns or raises

    @staticmethod
    async def _body(response: httpx2.Response) -> bytes:
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        length = response.headers.get("content-length")
        if (
            media_type != "application/json"
            or encoding != "identity"
            or (length is not None and (not length.isascii() or not length.isdigit()))
        ):
            raise SourceError("source_response_invalid")
        if length is not None and int(length) > MAX_RESPONSE_BYTES:
            raise SourceError("source_response_invalid")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                raise SourceError("source_response_invalid")
            body.extend(chunk)
        return bytes(body)
