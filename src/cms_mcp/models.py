"""Offline value models for the fixed mj5m-pzi6 count contract (1.0.0)."""

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION: Literal["1.0.0"] = "1.0.0"
MAX_RESPONSE_BYTES = 1_048_576
SPECIALTY = "CARDIOVASCULAR DISEASE (CARDIOLOGY)"
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        pass
    raise ValueError("timestamp_out_of_range")


Timestamp = Annotated[datetime, AfterValidator(_utc)]


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _ValueModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class SourceReference(_ValueModel):
    """Metadata evidence, not an immutable publisher release or downloaded CSV."""

    source_id: Literal["cms-pdc:mj5m-pzi6"] = "cms-pdc:mj5m-pzi6"
    distribution_id: Annotated[
        str, Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    ]
    download_url: Annotated[
        str,
        Field(
            pattern=(
                r"^https://data\.cms\.gov/provider-data/sites/default/files/resources/"
                r"[A-Za-z0-9_-]+/DAC_NationalDownloadableFile\.csv$"
            )
        ),
    ]
    catalog_released: date | None
    catalog_modified: date | None
    metadata_hash: Digest
    checked_at: Timestamp
    synthetic: bool
    publisher_immutable_release_id: None = None
    release_binding: Literal["unverified"] = "unverified"
    release_unknown_reason: Literal["live_query_has_no_verified_immutable_release_binding"] = (
        "live_query_has_no_verified_immutable_release_binding"
    )

    @property
    def source_ref(self) -> str:
        return "source:" + _hash(_canonical(self.model_dump(mode="json")))


def count_request() -> dict[str, Any]:
    """Return a fresh request for the sole approved aggregate; no caller filters."""
    return {
        "conditions": [
            {"property": "state", "value": "CA", "operator": "="},
            {"property": "pri_spec", "value": SPECIALTY, "operator": "="},
        ],
        "properties": ["state", "pri_spec"],
        "results": False,
        "count": True,
        "schema": True,
        "limit": 1,
        "offset": 0,
        "keys": True,
        "rowIds": False,
        "format": "json",
    }


class CountResponseError(ValueError):
    """A fixed error code only; never attach untrusted response contents."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CountResponseError("invalid_json")
        value[key] = item
    return value


def _reject_constant(_: str) -> None:
    raise CountResponseError("invalid_json")


def _read_count(body: bytes, distribution_id: str) -> int:
    if type(body) is not bytes or len(body) > MAX_RESPONSE_BYTES:
        raise CountResponseError("invalid_response_bytes")
    try:
        payload = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except (ValueError, UnicodeError, RecursionError):
        payload = None
    # Raise outside the handler so parser exceptions cannot retain rejected bytes
    # via __context__; `raise ... from None` only hides that chain when formatted.
    if payload is None:
        raise CountResponseError("invalid_json")
    if not isinstance(payload, dict):
        raise CountResponseError("invalid_response_shape")
    rows = payload.get("results")
    if rows is not None and not (type(rows) in (list, dict) and len(rows) == 0):
        raise CountResponseError("unexpected_results")
    if set(payload) - {"count", "query", "schema", "results"}:
        raise CountResponseError("unexpected_response_fields")
    count = payload.get("count")
    if type(count) is not int or count < 0:
        raise CountResponseError("invalid_count")
    expected = count_request() | {"resources": [{"id": distribution_id, "alias": "t"}]}
    try:
        matches = _canonical(payload.get("query")) == _canonical(expected)
    except (ValueError, RecursionError):
        matches = False
    if not matches:
        raise CountResponseError("query_mismatch")
    if "schema" in payload:
        schema = payload["schema"]
        if not isinstance(schema, dict) or set(schema) != {distribution_id}:
            raise CountResponseError("schema_mismatch")
        resource = schema[distribution_id]
        fields = resource.get("fields") if isinstance(resource, dict) else None
        if not isinstance(fields, dict) or any(
            not isinstance(fields.get(name), dict) or fields[name].get("type") != "text"
            for name in ("state", "pri_spec")
        ):
            raise CountResponseError("schema_mismatch")
    return count


class CountObservation(_ValueModel):
    """Normalized count; never represents distinct people or historical release binding.

    Use from_response at the raw payload boundary. Deserialization validates the
    normalized shape only; recomputing the byte hash needs the original bytes.
    """

    source: SourceReference
    record_count: Annotated[int, Field(ge=0)]
    response_hash: Digest
    retrieved_at: Timestamp
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    state: Literal["CA"] = "CA"
    primary_specialty: Literal["CARDIOVASCULAR DISEASE (CARDIOLOGY)"] = (
        "CARDIOVASCULAR DISEASE (CARDIOLOGY)"
    )
    counts_distinct_people: Literal[False] = False
    includes_secondary_specialties: Literal[False] = False
    query_semantics: Literal["timestamped_mutable_datastore_observation"] = (
        "timestamped_mutable_datastore_observation"
    )

    @classmethod
    def from_response(cls, body: bytes, *, source: SourceReference, retrieved_at: datetime) -> Self:
        count = _read_count(body, source.distribution_id)
        return cls(
            source=source, record_count=count, response_hash=_hash(body), retrieved_at=retrieved_at
        )

    @property
    def snapshot_id(self) -> str:
        # Full normalized scope and source evidence are part of this local identity.
        return "snapshot:" + self.normalized_hash

    @property
    def normalized_hash(self) -> str:
        return _hash(_canonical(self.model_dump(mode="json")))


class NormalizationStep(_ValueModel):
    operation: Literal["normalize_fixed_count"] = "normalize_fixed_count"
    input_hash: Digest
    output_hash: Digest
    executed_at: Timestamp
    implementation_version: Literal["0.0.1"] = "0.0.1"
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION


class Provenance(_ValueModel):
    """Lineage for this one normalization; caching adds serving metadata only."""

    observation: CountObservation
    lineage: tuple[NormalizationStep]
    served_at: Timestamp | None = None
    cache_status: Literal["not_served", "hit"] = "not_served"
    hash_origin: Literal["local"] = "local"
    publisher_checksum: None = None
    publisher_integrity: Literal["not_checked"] = "not_checked"
    dataset_quality: Literal["not_checked"] = "not_checked"
    validation_scope: Literal["fixed_count_response_contract_only"] = (
        "fixed_count_response_contract_only"
    )

    @model_validator(mode="after")
    def _consistent_evidence(self) -> Self:
        step = self.lineage[0]
        if (
            step.input_hash != self.observation.response_hash
            or step.output_hash != self.observation.normalized_hash
        ):
            raise ValueError("lineage_hash_mismatch")
        if step.executed_at < self.observation.retrieved_at:
            raise ValueError("normalization_precedes_retrieval")
        if (self.served_at is None) != (self.cache_status == "not_served"):
            raise ValueError("cache_status_time_mismatch")
        if self.served_at is not None and self.served_at < step.executed_at:
            raise ValueError("serving_precedes_normalization")
        return self

    @classmethod
    def from_observation(cls, observation: CountObservation, *, normalized_at: datetime) -> Self:
        return cls(
            observation=observation,
            lineage=(
                NormalizationStep(
                    input_hash=observation.response_hash,
                    output_hash=observation.normalized_hash,
                    executed_at=normalized_at,
                ),
            ),
        )

    def served_from_cache(self, served_at: datetime) -> Self:
        # Validated reconstruction: model_copy(update=...) would bypass validation.
        return type(self).model_validate(
            self.model_dump() | {"served_at": served_at, "cache_status": "hit"}
        )

    @property
    def provenance_id(self) -> str:
        return "provenance:" + _hash(_canonical(self.model_dump(mode="json")))
