"""Offline, transport-level checks for the sole approved CMS aggregate."""

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import anyio
import httpx2
import pytest

from cms_mcp import sources
from cms_mcp.models import count_request
from cms_mcp.sources import CMSClient, SourceError

EVIDENCE = Path(__file__).parents[2] / "docs/sources/mj5m-pzi6/evidence/2026-10-02"
NOW = datetime(2026, 10, 4, 19, tzinfo=UTC)
META = (EVIDENCE / "metadata-references.json").read_bytes()
COUNT = (EVIDENCE / "cardiology-count.json").read_bytes()


@pytest.mark.parametrize("offsets", [(-1, 0, 1, 2), (1, 0, 2, 3), (1, 3, 2, 4), (1, 2, 4, 3)])
def test_retrieval_rejects_backwards_acquisition_clock(offsets):
    ticks = iter(NOW + timedelta(seconds=i) for i in offsets)
    client = client_for(
        lambda r: response(COUNT if r.method == "POST" else META), clock=lambda: next(ticks)
    )
    assert_error("source_clock_invalid", lambda: client.retrieve(source()))


def test_dns_deadline_does_not_wait_for_default_executor_shutdown(monkeypatch):
    def stalled_resolver(*args, **kwargs):
        time.sleep(0.5)
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(sources.socket, "getaddrinfo", stalled_resolver)
    monkeypatch.setattr(sources, "TOTAL_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(
        sources.httpx2,
        "AsyncHTTPTransport",
        lambda **kwargs: httpx2.MockTransport(lambda request: response()),
    )
    started = time.monotonic()
    assert_error("source_timeout", CMSClient(clock=Clock()).metadata)
    assert time.monotonic() - started < 0.25


def response(body=META, *, status=200, headers=None):
    return httpx2.Response(
        status, content=body, headers={"content-type": "application/json", **(headers or {})}
    )


class Clock:
    def __init__(self):
        self.ticks = 0

    def __call__(self):
        value = NOW + timedelta(seconds=self.ticks)
        self.ticks += 1
        return value


def client_for(handler, clock=None):
    return CMSClient(clock=clock or Clock(), transport=httpx2.MockTransport(handler))


def source():
    return client_for(lambda request: response()).metadata()


def assert_error(code, operation):
    with pytest.raises(SourceError, match=f"^{code}$") as caught:
        operation()
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def test_metadata_and_exact_count_preserve_evidence():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["accept"] == "application/json"
        return response(COUNT if request.method == "POST" else META)

    client = client_for(handler)
    selected = client.metadata()
    assert selected.synthetic is False
    assert selected.metadata_hash == hashlib.sha256(META).hexdigest()
    assert selected.checked_at == NOW
    assert selected.catalog_released.isoformat() == "2026-09-10"
    assert selected.publisher_immutable_release_id is None
    provenance = client.retrieve(selected)
    assert provenance.observation.record_count == 5634
    assert provenance.observation.source == selected
    assert provenance.observation.retrieved_at == NOW + timedelta(seconds=2)
    assert provenance.lineage[0].executed_at == NOW + timedelta(seconds=4)
    assert provenance.publisher_integrity == "not_checked"
    assert provenance.dataset_quality == "not_checked"
    assert [(r.method, str(r.url)) for r in requests] == [
        ("GET", sources.METADATA_URL),
        ("GET", sources.METADATA_URL),
        ("POST", sources.COUNT_URL),
        ("GET", sources.METADATA_URL),
    ]
    assert json.loads(requests[2].content) == count_request()


@pytest.mark.parametrize(
    "path,value",
    [
        (("identifier",), "other"),
        (("title",), "Other file"),
        (("accessLevel",), "private"),
        (("landingPage",), "https://data.cms.gov.example.invalid/"),
        (("publisher", "identifier"), "other"),
        (("publisher", "data", "name"), "Unknown"),
        (
            ("distribution", 0, "data", "downloadURL"),
            "https://127.0.0.1/DAC_NationalDownloadableFile.csv",
        ),
        (
            ("distribution", 0, "data", "downloadURL"),
            "https://user@data.cms.gov/provider-data/sites/default/files/resources/a/DAC_NationalDownloadableFile.csv",
        ),
        (("distribution", 0, "data", "describedBy"), "https://example.invalid/dictionary.pdf"),
        (("distribution", 0, "data", "mediaType"), "application/zip"),
        (("distribution", 0, "identifier"), "not-a-uuid"),
    ],
)
def test_rejects_unverified_metadata(path, value):
    metadata = json.loads(META)
    cursor = metadata
    for component in path[:-1]:
        cursor = cursor[component]
    cursor[path[-1]] = value
    client = client_for(lambda request: response(json.dumps(metadata).encode()))
    assert_error("source_metadata_invalid", client.metadata)


@pytest.mark.parametrize("key", ["released", "modified"])
@pytest.mark.parametrize("value", ["missing", None])
def test_missing_catalog_dates_remain_unknown(key, value):
    metadata = json.loads(META)
    if value == "missing":
        metadata.pop(key)
    else:
        metadata[key] = value
    selected = client_for(lambda request: response(json.dumps(metadata).encode())).metadata()
    assert getattr(selected, "catalog_" + key) is None


@pytest.mark.parametrize(
    "value", ["", "2026-99-01", "20260910", 20260910, False, "2026-09-10T00:00:00Z"]
)
def test_present_invalid_release_is_rejected(value):
    metadata = json.loads(META)
    metadata["released"] = value
    assert_error(
        "source_metadata_invalid",
        client_for(lambda request: response(json.dumps(metadata).encode())).metadata,
    )


@pytest.mark.parametrize(
    "body",
    [
        b'{"identifier":"mj5m-pzi6","identifier":"DO_NOT_ECHO"}',
        b"not-json DO_NOT_ECHO",
        b"[]",
        b'{"value":NaN}',
    ],
)
def test_malformed_metadata_is_sanitized(body):
    assert_error("source_metadata_invalid", client_for(lambda request: response(body)).metadata)


@pytest.mark.parametrize("phase", ["before", "after"])
def test_metadata_drift_rejects_observation(phase):
    selected = source()
    changed = json.loads(META)
    changed["released"] = "2026-10-01"
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "POST":
            return response(COUNT)
        drift = phase == "before" or len(calls) == 3
        return response(json.dumps(changed).encode() if drift else META)

    assert_error("source_changed", lambda: client_for(handler).retrieve(selected))
    assert calls == (["GET"] if phase == "before" else ["GET", "POST", "GET"])


@pytest.mark.parametrize("change", ["count", "rows", "query", "resource"])
def test_invalid_count_contract_never_returns_provenance(change):
    body = json.loads(COUNT)
    if change == "count":
        body["count"] = True
    elif change == "rows":
        body["results"] = [{"DO_NOT_ECHO": "personal data"}]
    elif change == "query":
        body["query"]["conditions"][0]["value"] = "NY"
    else:
        body["query"]["resources"][0]["id"] = "00000000-0000-0000-0000-000000000000"
    client = client_for(
        lambda request: response(json.dumps(body).encode() if request.method == "POST" else META)
    )
    assert_error("count_response_invalid", lambda: client.retrieve(source()))


@pytest.mark.parametrize(
    "update,code",
    [
        ({"synthetic": True}, "live_source_required"),
        ({"metadata_hash": "0" * 64}, "source_changed"),
        ({"distribution_id": "00000000-0000-0000-0000-000000000000"}, "source_changed"),
        ({"source_id": "DO_NOT_ECHO"}, "source_scope_invalid"),
    ],
)
def test_source_scope_is_revalidated(update, code):
    selected = source().model_copy(update=update)
    calls = []
    client = client_for(lambda request: calls.append(request) or response())
    assert_error(code, lambda: client.retrieve(selected))
    if code in ("live_source_required", "source_scope_invalid"):
        assert not calls


@pytest.mark.parametrize("status", [301, 302, 307, 400, 401, 404, 500])
def test_unexpected_status_never_follows_or_retries(status):
    calls = []
    client = client_for(
        lambda request: (
            calls.append(request)
            or response(status=status, headers={"location": "http://127.0.0.1/DO_NOT_ECHO"})
        )
    )
    assert_error("source_http_error", client.metadata)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "headers,body",
    [
        ({"content-type": "text/html"}, b"DO_NOT_ECHO"),
        ({"content-encoding": "gzip"}, b""),
        ({"content-length": "1048577"}, b""),
        ({"content-length": "garbage"}, b""),
        ({}, b"x" * 1048577),
    ],
)
def test_response_limits(headers, body):
    assert_error(
        "source_response_invalid",
        client_for(lambda request: response(body, headers=headers)).metadata,
    )


@pytest.mark.parametrize("failure", [429, 503, "timeout"])
def test_one_retry_preserves_request_then_succeeds(failure, monkeypatch):
    monkeypatch.setattr(sources, "RETRY_DELAY_SECONDS", 0)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == "timeout":
                raise httpx2.ReadTimeout("DO_NOT_ECHO")
            return response(status=failure, headers={"retry-after": "0"})
        return response()

    client_for(handler).metadata()
    assert len(calls) == 2
    assert [(r.method, str(r.url), r.content) for r in calls] == [
        (calls[0].method, str(calls[0].url), calls[0].content)
    ] * 2


@pytest.mark.parametrize("failure", [429, 503, "timeout", "network"])
def test_retry_count_and_sanitized_transport_errors(failure, monkeypatch):
    monkeypatch.setattr(sources, "RETRY_DELAY_SECONDS", 0)
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx2.ReadTimeout("DO_NOT_ECHO")
        if failure == "network":
            raise httpx2.ConnectError("DO_NOT_ECHO")
        return response(status=failure, headers={"retry-after": "0"})

    code = "source_timeout" if failure == "timeout" else "source_unavailable"
    assert_error(code, client_for(handler).metadata)
    assert len(calls) == (1 if failure == "network" else 2)


def test_retry_after_larger_than_budget_does_not_retry():
    calls = []
    client = client_for(
        lambda request: (
            calls.append(request) or response(status=503, headers={"retry-after": "9999"})
        )
    )
    assert_error("source_unavailable", client.metadata)
    assert len(calls) == 1


def test_total_deadline_covers_stalled_transport(monkeypatch):
    monkeypatch.setattr(sources, "TOTAL_TIMEOUT_SECONDS", 0.02)

    async def handler(request):
        await anyio.sleep(1)
        return response()

    assert_error("source_timeout", client_for(handler).metadata)


def test_stream_body_cap_is_enforced_without_content_length():
    class Chunks(httpx2.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(20):
                yield b"x" * 65536

    client = client_for(
        lambda request: httpx2.Response(
            200, headers={"content-type": "application/json"}, stream=Chunks()
        )
    )
    assert_error("source_response_invalid", client.metadata)


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.2.3.4", "169.254.169.254", "::1", "fe80::1", "0.0.0.0"]
)
def test_default_transport_rejects_nonpublic_addresses(address, monkeypatch):
    calls = []

    def resolve(*args, **kwargs):
        return [(2, 1, 6, "", (address, 443))]

    monkeypatch.setattr(sources.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(
        sources.httpx2,
        "AsyncHTTPTransport",
        lambda **kwargs: httpx2.MockTransport(lambda request: calls.append(request) or response()),
    )
    assert_error("source_address_rejected", CMSClient(clock=Clock()).metadata)
    assert not calls


def test_default_transport_pins_public_ip_and_keeps_verified_cms_hostname(monkeypatch):
    requests = []
    options = []
    resolutions = []

    def resolve(host, port, **kwargs):
        resolutions.append((host, port))
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    def transport(**kwargs):
        options.append(kwargs)
        return httpx2.MockTransport(lambda request: requests.append(request) or response())

    monkeypatch.setattr(sources.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(sources.httpx2, "AsyncHTTPTransport", transport)
    CMSClient(clock=Clock()).metadata()
    assert options == [{"verify": True, "trust_env": False, "retries": 0}]
    assert resolutions == [("data.cms.gov", 443)]
    assert str(requests[0].url) == sources.METADATA_URL.replace("data.cms.gov", "8.8.8.8")
    assert requests[0].headers["host"] == "data.cms.gov"
    assert requests[0].extensions["sni_hostname"] == "data.cms.gov"


def test_compression_is_rejected_before_body_decoding():
    class Bomb(httpx2.AsyncByteStream):
        async def __aiter__(self):
            pytest.fail("Compressed payload must not be consumed")
            yield b""

    client = client_for(
        lambda request: httpx2.Response(
            200,
            headers={"content-type": "application/json", "content-encoding": "gzip"},
            stream=Bomb(),
        )
    )
    assert_error("source_response_invalid", client.metadata)


def test_total_deadline_includes_retry_wait(monkeypatch):
    monkeypatch.setattr(sources, "TOTAL_TIMEOUT_SECONDS", 0.02)
    calls = []
    client = client_for(
        lambda request: calls.append(request) or response(status=503, headers={"retry-after": "1"})
    )
    assert_error("source_timeout", client.metadata)
    assert len(calls) == 1


def test_total_deadline_is_shared_by_entire_retrieval(monkeypatch):
    monkeypatch.setattr(sources, "TOTAL_TIMEOUT_SECONDS", 0.05)
    selected = source()
    calls = []

    async def handler(request):
        calls.append(request.method)
        await anyio.sleep(0.02)
        return response(COUNT if request.method == "POST" else META)

    assert_error("source_timeout", lambda: client_for(handler).retrieve(selected))
    assert calls == ["GET", "POST", "GET"]


def test_count_retry_keeps_count_only_request(monkeypatch):
    monkeypatch.setattr(sources, "RETRY_DELAY_SECONDS", 0)
    posts = []

    def handler(request):
        if request.method == "POST":
            posts.append(json.loads(request.content))
            return response(COUNT) if len(posts) == 2 else response(status=503)
        return response()

    client_for(handler).retrieve(source())
    assert posts == [count_request(), count_request()]


@pytest.mark.parametrize("address", ["224.0.0.1", "ff02::1"])
def test_default_transport_rejects_multicast_addresses(address, monkeypatch):
    calls = []

    def resolve(*args, **kwargs):
        return [(2, 1, 6, "", (address, 443))]

    monkeypatch.setattr(sources.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(
        sources.httpx2,
        "AsyncHTTPTransport",
        lambda **kwargs: httpx2.MockTransport(lambda request: calls.append(request) or response()),
    )
    assert_error("source_address_rejected", CMSClient(clock=Clock()).metadata)
    assert not calls
