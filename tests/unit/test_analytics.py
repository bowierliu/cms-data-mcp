"""Deterministic one-row analytics; fabricated counts and no network or personal rows."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from cms_mcp.analytics import (
    AnalyticsError,
    Filter,
    QueryRequest,
    QueryResult,
    ValidationReport,
    query_count,
    render_csv,
    validate_count,
)
from cms_mcp.models import CountObservation, Provenance
from cms_mcp.synthetic import load_synthetic_fixture

ARTIFACT = "artifact:" + "a" * 64
VALIDATION = "validation:" + "b" * 64
VALIDATED = datetime(2026, 10, 4, 18, tzinfo=UTC)
QUERIED = VALIDATED + timedelta(seconds=1)


@pytest.fixture
def provenance():
    fixture = load_synthetic_fixture()
    observation = CountObservation.from_response(
        fixture.body, source=fixture.source, retrieved_at=fixture.retrieved_at
    )
    return Provenance.from_observation(observation, normalized_at=fixture.normalized_at)


def query(provenance, request=None, report=None, **kwargs):
    return query_count(
        ARTIFACT,
        provenance,
        VALIDATION,
        report or validate_count(ARTIFACT, provenance, executed_at=VALIDATED),
        request or QueryRequest(),
        executed_at=QUERIED,
        **kwargs,
    )


def test_report_distinguishes_contract_passes_from_unchecked_dataset_quality(provenance):
    report = validate_count(ARTIFACT, provenance, executed_at=VALIDATED)
    assert report.overall == "pass"
    assert report.artifact_id == ARTIFACT
    assert report.source_ref == provenance.observation.source.source_ref
    assert report.snapshot_id == provenance.observation.snapshot_id
    assert report.scope.counts_distinct_people is False
    assert report.scope.synthetic is True
    checks = {check.id: check for check in report.checks}
    assert all(check.status == "pass" for check in checks.values() if check.required)
    for name in (
        "raw_response_rehash",
        "publisher_integrity",
        "raw_row_quality",
        "duplicates",
        "null_patterns",
        "immutable_release_binding",
    ):
        assert checks[name].status == "not_checked"
    assert checks["stored_artifact_integrity"].observed == "loaded_by_verified_store"
    assert ValidationReport.model_validate_json(report.model_dump_json()) == report


def test_query_default_is_one_aggregate_row_and_preserves_parent_scope(provenance):
    result = query(provenance)
    assert result.columns == ("state", "primary_specialty", "record_count")
    assert result.rows == (("CA", "CARDIOVASCULAR DISEASE (CARDIOLOGY)", 5),)
    assert result.row_count == 1
    assert result.truncated is False
    assert result.scope.counts_distinct_people is False
    assert result.artifact_id == ARTIFACT
    assert result.validation_id == VALIDATION
    assert result.source_ref == provenance.observation.source.source_ref
    assert result.snapshot_id == provenance.observation.snapshot_id
    assert result.executed_at == QUERIED
    assert result.operation == "query_fixed_count"
    assert QueryResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "field,op,value,matched",
    [
        ("state", "eq", "CA", True),
        ("state", "eq", "NY", False),
        ("record_count", "eq", 5, True),
        ("record_count", "eq", 0, False),
        ("record_count", "gte", 5, True),
        ("record_count", "gte", 6, False),
        ("record_count", "lte", 5, True),
        ("record_count", "lte", 4, False),
    ],
)
def test_filters_match_local_aggregate_not_upstream_rows(provenance, field, op, value, matched):
    request = QueryRequest(
        select=["record_count", "state"], filters=[Filter(field=field, op=op, value=value)], limit=1
    )
    result = query(provenance, request)
    assert result.rows == (((5, "CA"),) if matched else ())
    assert result.row_count == int(matched)
    assert result.truncated is False


def test_csv_projection_and_empty_result_have_exact_headers(provenance):
    assert render_csv(query(provenance, QueryRequest(select=["record_count", "state"]))) == (
        b"record_count,state\r\n5,CA\r\n"
    )
    request = QueryRequest(filters=[Filter(field="record_count", op="gte", value=6)])
    assert render_csv(query(provenance, request)) == b"state,primary_specialty,record_count\r\n"


@pytest.mark.parametrize("name", ["county", "city", "zip", "ZIP", "citytown", "county_fips"])
def test_geography_never_silently_maps_to_state(provenance, name):
    for request in (
        QueryRequest(select=[name]),
        QueryRequest(filters=[Filter(field=name, op="eq", value="synthetic")]),
    ):
        with pytest.raises(AnalyticsError, match="^unsupported_geography$"):
            query(provenance, request)


@pytest.mark.parametrize(
    "raw",
    [
        {"select": []},
        {"select": ["state"] * 4},
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"limit": "1"},
        {"sql": "DO_NOT_ECHO"},
        {"filters": [{"field": "state", "op": "contains", "value": "CA"}]},
        {"filters": [{"field": "record_count", "op": "eq", "value": True}]},
        {"filters": [{"field": "state", "op": "eq", "value": "x" * 129}]},
        {"filters": [{"field": "state", "op": "eq", "value": "CA"}] * 4},
    ],
)
def test_request_input_limits_and_types(raw):
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(raw)


@pytest.mark.parametrize(
    "query_request",
    [
        QueryRequest(select=["state", "state"]),
        QueryRequest(select=["npi"]),
        QueryRequest(select=["=DO_NOT_ECHO"]),
        QueryRequest(filters=[Filter(field="record_count", op="eq", value="5")]),
        QueryRequest(filters=[Filter(field="state", op="eq", value=5)]),
        QueryRequest(filters=[Filter(field="state", op="gte", value="CA")]),
    ],
)
def test_semantically_invalid_query_is_safe(provenance, query_request):
    with pytest.raises(AnalyticsError) as caught:
        query(provenance, query_request)
    assert str(caught.value) == "invalid_query"
    assert caught.value.__context__ is None
    assert "DO_NOT_ECHO" not in repr(caught.value)


@pytest.mark.parametrize("field", ["state", "primary_specialty"])
@pytest.mark.parametrize("text", ["UNAPPROVED_FREE_TEXT", "", "CA ", "ca"])
def test_free_text_filters_are_rejected_before_result_creation(provenance, field, text):
    request = QueryRequest(filters=[Filter(field=field, op="eq", value=text)])
    with pytest.raises(AnalyticsError) as caught:
        query(provenance, request)
    assert str(caught.value) == "invalid_query"
    assert caught.value.__context__ is None
    assert "UNAPPROVED_FREE_TEXT" not in repr(caught.value)


@pytest.mark.parametrize("field", ["state", "primary_specialty"])
def test_saved_empty_result_cannot_retain_arbitrary_filter_text(provenance, field):
    result = query(provenance)
    request = QueryRequest(filters=[Filter(field=field, op="eq", value="UNAPPROVED_FREE_TEXT")])
    changes = {"request": request, "rows": (), "row_count": 0}
    with pytest.raises(ValidationError):
        QueryResult.model_validate(result.model_dump() | changes)
    with pytest.raises(AnalyticsError, match="^invalid_query_result$"):
        render_csv(result.model_copy(update=changes))


@pytest.mark.parametrize("state", ["AK", "DC", "PR", "AS", "GU", "MP", "VI"])
def test_approved_state_codes_can_filter_to_empty_results(provenance, state):
    result = query(provenance, QueryRequest(filters=[Filter(field="state", op="eq", value=state)]))
    assert result.rows == ()
    assert result.row_count == 0


def test_approved_specialty_filter_preserves_fixed_row(provenance):
    result = query(
        provenance,
        QueryRequest(
            filters=[
                Filter(
                    field="primary_specialty",
                    op="eq",
                    value="CARDIOVASCULAR DISEASE (CARDIOLOGY)",
                )
            ]
        ),
    )
    assert result.row_count == 1
    assert result.rows[0][-1] == 5


def test_query_requires_matching_passing_report(provenance):
    report = validate_count(ARTIFACT, provenance, executed_at=VALIDATED)
    for field, value in (
        ("artifact_id", "artifact:" + "c" * 64),
        ("source_ref", "source:" + "c" * 64),
        ("snapshot_id", "snapshot:" + "c" * 64),
    ):
        changed = ValidationReport.model_validate(report.model_dump() | {field: value})
        with pytest.raises(AnalyticsError, match="^validation_scope_mismatch$"):
            query(provenance, report=changed)
    raw = report.model_dump()
    raw["checks"][0]["status"] = "fail"
    raw["overall"] = "fail"
    failed = ValidationReport.model_validate(raw)
    with pytest.raises(AnalyticsError, match="^validation_failed$"):
        query(provenance, report=failed)


def test_report_cannot_omit_required_checks_or_hide_failure(provenance):
    report = validate_count(ARTIFACT, provenance, executed_at=VALIDATED)
    raw = report.model_dump()
    raw["checks"] = raw["checks"][1:]
    with pytest.raises(ValidationError):
        ValidationReport.model_validate(raw)
    raw = report.model_dump()
    raw["checks"][0]["status"] = "fail"
    with pytest.raises(ValidationError):
        ValidationReport.model_validate(raw)


def test_zero_count_remains_zero_and_invalid_provenance_is_rejected(provenance):
    raw = provenance.observation.model_dump()
    zero = CountObservation.model_validate(raw | {"record_count": 0})
    valid = Provenance.from_observation(zero, normalized_at=provenance.lineage[0].executed_at)
    assert query(valid).rows[0][-1] == 0
    for value in (-1, True, "5"):
        corrupt = provenance.model_copy(
            update={
                "observation": provenance.observation.model_copy(update={"record_count": value})
            }
        )
        with pytest.raises(AnalyticsError, match="^invalid_provenance$"):
            validate_count(ARTIFACT, corrupt, executed_at=VALIDATED)


def test_validation_and_query_time_order(provenance):
    for stamp in (datetime(2026, 10, 4), provenance.observation.retrieved_at):
        with pytest.raises(AnalyticsError, match="^invalid_execution_time$"):
            validate_count(ARTIFACT, provenance, executed_at=stamp)
    report = validate_count(ARTIFACT, provenance, executed_at=VALIDATED)
    with pytest.raises(AnalyticsError, match="^invalid_execution_time$"):
        query_count(
            ARTIFACT,
            provenance,
            VALIDATION,
            report,
            QueryRequest(),
            executed_at=VALIDATED - timedelta(seconds=1),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"rows": (("=DO_NOT_ECHO", "CARDIOVASCULAR DISEASE (CARDIOLOGY)", 5),)},
        {"rows": (("CA", "CARDIOVASCULAR DISEASE (CARDIOLOGY)", -1),)},
        {"rows": (("CA", "CARDIOVASCULAR DISEASE (CARDIOLOGY)", True),)},
        {"rows": (("CA", "CARDIOVASCULAR DISEASE (CARDIOLOGY)"),)},
        {"rows": (), "row_count": 1},
        {"columns": ("npi", "primary_specialty", "record_count")},
        {"columns": ("state", "state", "record_count")},
        {"rows": (("CA", "CARDIOVASCULAR DISEASE (CARDIOLOGY)", 5),) * 2, "row_count": 2},
        {"truncated": True},
    ],
)
def test_persisted_result_deep_validation_blocks_forged_csv_values(provenance, changes):
    result = query(provenance)
    with pytest.raises(ValidationError):
        QueryResult.model_validate(result.model_dump() | changes)
    forged = result.model_copy(update=changes)
    with pytest.raises(AnalyticsError, match="^invalid_query_result$"):
        render_csv(forged)


def test_json_roundtrip_rejects_extra_fields_and_unknown_operation(provenance):
    result = json.loads(query(provenance).model_dump_json())
    result["operation"] = "arbitrary_sql"
    with pytest.raises(ValidationError):
        QueryResult.model_validate_json(json.dumps(result))
