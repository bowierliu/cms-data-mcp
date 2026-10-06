"""Synthetic count payloads; no network, personal values, or CMS row retrieval."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from cms_mcp.models import CountObservation, CountResponseError, Provenance, SourceReference

ROOT = Path(__file__).resolve().parents[2]
CHECKED = datetime(2026, 10, 3, 10, tzinfo=UTC)
RETRIEVED = CHECKED + timedelta(seconds=1)
DISTRIBUTION = "11111111-2222-4333-8444-555555555555"


@pytest.fixture
def source():
    return SourceReference(
        distribution_id=DISTRIBUTION,
        download_url="https://data.cms.gov/provider-data/sites/default/files/resources/"
        "synthetic/DAC_NationalDownloadableFile.csv",
        catalog_released=date(2026, 9, 10),
        catalog_modified=date(2026, 8, 18),
        metadata_hash="a" * 64,
        checked_at=CHECKED,
        synthetic=True,
    )


@pytest.fixture
def payload():
    # Exact approved request shape; all observation values below are synthetic.
    request = json.loads((ROOT / "docs/sources/mj5m-pzi6/count-request.json").read_text())
    request["resources"] = [{"id": DISTRIBUTION, "alias": "t"}]
    return {"count": 7, "query": request}


def observe(source, payload, **kwargs):
    return CountObservation.from_response(
        json.dumps(payload).encode(), source=source, retrieved_at=RETRIEVED, **kwargs
    )


def test_normalized_count_and_local_hash(source, payload):
    observation = observe(source, payload)
    assert observation.record_count == 7
    assert observation.state == "CA"
    assert observation.primary_specialty == "CARDIOVASCULAR DISEASE (CARDIOLOGY)"
    assert observation.response_hash == hashlib.sha256(json.dumps(payload).encode()).hexdigest()
    assert observation.counts_distinct_people is False
    assert observation.source.synthetic is True
    assert "query" not in observation.model_dump()


def test_unknown_release_is_explicit_and_cannot_be_invented(source):
    assert source.publisher_immutable_release_id is None
    assert source.release_binding == "unverified"
    with pytest.raises(ValidationError):
        SourceReference(**(source.model_dump() | {"publisher_immutable_release_id": "latest"}))


@pytest.mark.parametrize("count", [True, False, "7", 7.0, None, -1, [], {}])
def test_count_must_be_nonnegative_integer(source, payload, count):
    payload["count"] = count
    with pytest.raises(CountResponseError, match="invalid_count"):
        observe(source, payload)


def test_zero_count_is_valid(source, payload):
    payload["count"] = 0
    assert observe(source, payload).record_count == 0


@pytest.mark.parametrize(
    "change", ["state", "specialty", "projection", "resource", "flag", "extra"]
)
def test_query_drift_is_rejected(source, payload, change):
    query = payload["query"]
    if change == "state":
        query["conditions"][0]["value"] = "NY"
    elif change == "specialty":
        query["conditions"][1]["property"] = "sec_spec_1"
    elif change == "projection":
        query["properties"] = ["citytown"]
    elif change == "resource":
        query["resources"][0]["id"] = "00000000-0000-4000-8000-000000000000"
    elif change == "flag":
        query["count"] = 1  # Python equality must not confuse bool and int.
    else:
        query["unexpected"] = "value"
    with pytest.raises(CountResponseError, match="query_mismatch"):
        observe(source, payload)


@pytest.mark.parametrize("rows", [[{"synthetic_secret": "DO_NOT_ECHO"}], {"a": 1}, False, ""])
def test_forbidden_rows_rejected_without_echoing_input(source, payload, rows):
    payload["results"] = rows
    with pytest.raises(CountResponseError) as caught:
        observe(source, payload)
    assert str(caught.value) == "unexpected_results"
    assert "DO_NOT_ECHO" not in repr(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("rows", [None, [], {}])
def test_empty_results_are_allowed(source, payload, rows):
    payload["results"] = rows
    assert observe(source, payload).record_count == 7


@pytest.mark.parametrize(
    "body", [b"{", b"[]", b"\xff", b'{"count":0,"count":1}', b'{"count":NaN}', b"x" * (1048576 + 1)]
)
def test_malformed_or_oversized_response(source, body):
    with pytest.raises(CountResponseError):
        CountObservation.from_response(body, source=source, retrieved_at=RETRIEVED)


@pytest.mark.parametrize("body", [b'{"synthetic_secret":"DO_NOT_ECHO",', b"DO_NOT_ECHO\xff"])
def test_parser_errors_do_not_retain_rejected_payload_context(source, body):
    with pytest.raises(CountResponseError) as caught:
        CountObservation.from_response(body, source=source, retrieved_at=RETRIEVED)
    assert str(caught.value) == "invalid_json"
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_optional_schema_checks_resource_and_required_types(source, payload):
    fields = {name: {"type": "text"} for name in ("state", "pri_spec")}
    payload["schema"] = {DISTRIBUTION: {"fields": fields}}
    assert observe(source, payload).record_count == 7
    fields["state"]["type"] = "integer"
    with pytest.raises(CountResponseError, match="schema_mismatch"):
        observe(source, payload)
    payload["schema"] = {"wrong-resource": {"fields": fields}}
    with pytest.raises(CountResponseError, match="schema_mismatch"):
        observe(source, payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("checked_at", datetime(2026, 10, 3)),
        ("metadata_hash", "not-a-hash"),
        ("distribution_id", "not-a-uuid"),
        ("download_url", "https://evil.invalid/DAC_NationalDownloadableFile.csv"),
        ("extra", "value"),
    ],
)
def test_invalid_source_evidence(source, field, value):
    with pytest.raises(ValidationError):
        SourceReference(**(source.model_dump() | {field: value}))


def test_utc_roundtrip_and_immutable_values(source, payload):
    offset_time = CHECKED.astimezone(timezone(timedelta(hours=-7)))
    equivalent = SourceReference(**(source.model_dump() | {"checked_at": offset_time}))
    assert equivalent.checked_at.tzinfo == UTC
    assert equivalent.source_ref == source.source_ref
    observation = observe(source, payload)
    assert CountObservation.model_validate_json(observation.model_dump_json()) == observation
    with pytest.raises(ValidationError):
        observation.record_count = 12
    with pytest.raises(ValidationError):
        observation.source.synthetic = False


def test_snapshot_binds_bytes_scope_source_and_retrieval_time(source, payload):
    observation = observe(source, payload)
    assert observe(source, payload).snapshot_id == observation.snapshot_id
    later = CountObservation.from_response(
        json.dumps(payload).encode(), source=source, retrieved_at=RETRIEVED + timedelta(seconds=1)
    )
    assert later.snapshot_id != observation.snapshot_id
    payload["count"] = 8
    assert observe(source, payload).snapshot_id != observation.snapshot_id
    changed = SourceReference(**(source.model_dump() | {"metadata_hash": "b" * 64}))
    assert observe(changed, payload).source.source_ref != source.source_ref


def test_cache_serving_preserves_original_evidence_and_lineage(source, payload):
    observation = observe(source, payload)
    provenance = Provenance.from_observation(observation, normalized_at=RETRIEVED)
    served = provenance.served_from_cache(RETRIEVED + timedelta(days=1))
    assert served.observation == observation
    assert served.observation.retrieved_at == RETRIEVED
    assert served.observation.source.checked_at == CHECKED
    assert served.lineage == provenance.lineage
    assert served.cache_status == "hit"
    assert served.served_at == RETRIEVED + timedelta(days=1)
    assert provenance.served_at is None
    assert served.hash_origin == "local"
    assert served.publisher_checksum is None
    assert served.dataset_quality == "not_checked"
    assert Provenance.model_validate_json(served.model_dump_json()) == served


def test_cache_rejects_naive_or_backwards_serving_times(source, payload):
    provenance = Provenance.from_observation(observe(source, payload), normalized_at=RETRIEVED)
    for timestamp in (datetime(2026, 10, 3), RETRIEVED - timedelta(seconds=1)):
        with pytest.raises(ValidationError):
            provenance.served_from_cache(timestamp)


def test_provenance_cannot_deserialize_tampered_lineage(source, payload):
    provenance = Provenance.from_observation(observe(source, payload), normalized_at=RETRIEVED)
    raw = json.loads(provenance.model_dump_json())
    raw["lineage"][0]["input_hash"] = "b" * 64
    with pytest.raises(ValidationError):
        Provenance.model_validate_json(json.dumps(raw))
