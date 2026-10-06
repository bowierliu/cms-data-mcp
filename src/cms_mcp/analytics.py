"""Deterministic validation and projection of one fixed, non-identifying count row."""

import csv
import io
import re
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from cms_mcp.models import SPECIALTY, Provenance, Timestamp

ArtifactID = Annotated[str, Field(pattern=r"^artifact:[0-9a-f]{64}$", min_length=73, max_length=73)]
ValidationID = Annotated[
    str, Field(pattern=r"^validation:[0-9a-f]{64}$", min_length=75, max_length=75)
]
SourceID = Annotated[str, Field(pattern=r"^source:[0-9a-f]{64}$", min_length=71, max_length=71)]
SnapshotID = Annotated[str, Field(pattern=r"^snapshot:[0-9a-f]{64}$", min_length=73, max_length=73)]
Column = Literal["state", "primary_specialty", "record_count"]
FieldName = Annotated[str, Field(min_length=1, max_length=64)]
FilterText = Annotated[str, Field(max_length=128)]
CheckText = Annotated[str, Field(max_length=512)]
Cell = str | int
_COLUMNS = ("state", "primary_specialty", "record_count")
# Finite public category values only: saved query requests must never retain
# arbitrary caller text, even when a filter produces an empty result.
_STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY "
    "DC AS GU MP PR VI".split()
)
_REQUIRED_CHECKS = frozenset(
    (
        "stored_artifact_integrity",
        "response_contract_at_ingestion",
        "normalized_schema",
        "normalization_lineage",
        "nonnegative_record_count",
        "fixed_count_scope",
    )
)
_UNCHECKED = frozenset(
    (
        "raw_response_rehash",
        "publisher_integrity",
        "raw_row_quality",
        "duplicates",
        "null_patterns",
        "immutable_release_binding",
    )
)


class AnalyticsError(ValueError):
    """A fixed lower_snake_case code; no caller text or exception context."""


class _Model(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class CountScope(_Model):
    synthetic: bool
    state: Literal["CA"] = "CA"
    primary_specialty: Literal["CARDIOVASCULAR DISEASE (CARDIOLOGY)"] = (
        "CARDIOVASCULAR DISEASE (CARDIOLOGY)"
    )
    count_unit: Literal["enrollment_location_records"] = "enrollment_location_records"
    counts_distinct_people: Literal[False] = False
    includes_secondary_specialties: Literal[False] = False
    completeness: Literal["complete_for_fixed_aggregate_view"] = "complete_for_fixed_aggregate_view"
    query_semantics: Literal["local_filter_of_saved_aggregate"] = "local_filter_of_saved_aggregate"


class ValidationCheck(_Model):
    id: Annotated[str, Field(pattern=r"^[a-z_]+$", max_length=64)]
    severity: Literal["error", "info"]
    required: bool
    observed: CheckText | int
    expected: CheckText
    status: Literal["pass", "fail", "warning", "not_checked"]
    explanation: CheckText


class ValidationReport(_Model):
    artifact_id: ArtifactID
    source_ref: SourceID
    snapshot_id: SnapshotID
    scope: CountScope
    contract_version: Literal["1.0.0"] = "1.0.0"
    implementation_version: Literal["0.0.1"] = "0.0.1"
    operation: Literal["validate_fixed_count"] = "validate_fixed_count"
    executed_at: Timestamp
    overall: Literal["pass", "fail"]
    checks: Annotated[tuple[ValidationCheck, ...], Field(min_length=12, max_length=12)]

    @model_validator(mode="after")
    def _consistent_checks(self) -> Self:
        names = {check.id for check in self.checks}
        if names != _REQUIRED_CHECKS | _UNCHECKED:
            raise ValueError("invalid_validation_checks")
        for check in self.checks:
            required = check.id in _REQUIRED_CHECKS
            if check.required != required or check.severity != ("error" if required else "info"):
                raise ValueError("invalid_validation_checks")
            if not required and check.status != "not_checked":
                raise ValueError("unsupported_validation_claim")
        passed = all(check.status == "pass" for check in self.checks if check.required)
        if self.overall != ("pass" if passed else "fail"):
            raise ValueError("validation_overall_mismatch")
        return self


class Filter(_Model):
    field: FieldName
    op: Literal["eq", "gte", "lte"]
    value: FilterText | int = Field(
        description=(
            "record_count: integer; state: uppercase US state/DC/territory code; "
            "primary_specialty: exact CARDIOVASCULAR DISEASE (CARDIOLOGY) only. "
            "Arbitrary free text is rejected."
        )
    )


class QueryRequest(_Model):
    select: Annotated[list[FieldName], Field(min_length=1, max_length=3)] = Field(
        default_factory=lambda: ["state", "primary_specialty", "record_count"]
    )
    filters: Annotated[list[Filter], Field(max_length=3)] = Field(default_factory=list)
    limit: Annotated[int, Field(ge=1, le=100)] = 100


def _validate_query(request: QueryRequest) -> None:
    fields = request.select + [condition.field for condition in request.filters]
    if any(
        re.search(r"county|city|zip|postal|fips|geograph", field, flags=re.IGNORECASE)
        for field in fields
    ):
        raise AnalyticsError("unsupported_geography")
    if len(set(request.select)) != len(request.select) or any(
        field not in _COLUMNS for field in fields
    ):
        raise AnalyticsError("invalid_query")
    for condition in request.filters:
        if condition.field == "record_count":
            valid = type(condition.value) is int
        else:
            allowed = _STATE_CODES if condition.field == "state" else {SPECIALTY}
            valid = (
                type(condition.value) is str and condition.op == "eq" and condition.value in allowed
            )
        if not valid:
            raise AnalyticsError("invalid_query")


def _rows(request: QueryRequest, record_count: int) -> tuple[tuple[Cell, ...], ...]:
    row: dict[str, Cell] = {
        "state": "CA",
        "primary_specialty": SPECIALTY,
        "record_count": record_count,
    }
    for condition in request.filters:
        actual = row[condition.field]
        if condition.op == "eq":
            matched = actual == condition.value
        elif isinstance(actual, int) and isinstance(condition.value, int):
            matched = (
                actual >= condition.value if condition.op == "gte" else actual <= condition.value
            )
        else:
            raise AnalyticsError("invalid_query")
        if not matched:
            return ()
    return (tuple(row[column] for column in request.select),)


class QueryResult(_Model):
    artifact_id: ArtifactID
    validation_id: ValidationID
    source_ref: SourceID
    snapshot_id: SnapshotID
    scope: CountScope
    request: QueryRequest
    input_record_count: Annotated[int, Field(ge=0)]
    normalization_executed_at: Timestamp
    validation_executed_at: Timestamp
    columns: Annotated[tuple[Column, ...], Field(min_length=1, max_length=3)]
    rows: Annotated[tuple[tuple[Cell, ...], ...], Field(max_length=1)]
    row_count: Annotated[int, Field(ge=0, le=1)]
    truncated: Literal[False] = False
    executed_at: Timestamp
    operation: Literal["query_fixed_count"] = "query_fixed_count"
    implementation_version: Literal["0.0.1"] = "0.0.1"
    contract_version: Literal["1.0.0"] = "1.0.0"

    @model_validator(mode="after")
    def _exact_result(self) -> Self:
        _validate_query(self.request)
        if not self.normalization_executed_at <= self.validation_executed_at <= self.executed_at:
            raise ValueError("invalid_execution_time")
        if self.columns != tuple(self.request.select):
            raise ValueError("query_columns_mismatch")
        if self.row_count != len(self.rows) or self.rows != _rows(
            self.request, self.input_record_count
        ):
            raise ValueError("query_rows_mismatch")
        return self


def _provenance(value: Provenance) -> Provenance:
    try:
        return Provenance.model_validate(value)
    except (ValidationError, RecursionError):
        pass
    raise AnalyticsError("invalid_provenance")


def _time(value: datetime, earliest: datetime) -> datetime:
    try:
        stamp = TypeAdapter(Timestamp).validate_python(value, strict=True)
        if stamp >= earliest:
            return stamp
    except (ValidationError, OverflowError):
        pass
    raise AnalyticsError("invalid_execution_time")


def _id(value: str, prefix: str) -> str:
    if type(value) is not str or re.fullmatch(prefix + r":[0-9a-f]{64}", value) is None:
        raise AnalyticsError("invalid_" + prefix + "_id")
    return value


def _pass(name: str, observed: str | int, expected: str, explanation: str) -> ValidationCheck:
    return ValidationCheck(
        id=name,
        severity="error",
        required=True,
        observed=observed,
        expected=expected,
        status="pass",
        explanation=explanation,
    )


def _not_checked(name: str, explanation: str) -> ValidationCheck:
    return ValidationCheck(
        id=name,
        severity="info",
        required=False,
        observed="not_available_in_saved_aggregate",
        expected="independent_evidence_required",
        status="not_checked",
        explanation=explanation,
    )


def validate_count(
    artifact_id: str, provenance: Provenance, *, executed_at: datetime
) -> ValidationReport:
    """Report on a caller-loaded, store-verified artifact; never access files or raw bytes.

    The application must verify the immutable store manifest before calling this
    operation. Response-contract checking happened at ingestion; it is not rerun
    without the original response bytes. Structural/lineage checks run here.
    """
    _id(artifact_id, "artifact")
    evidence = _provenance(provenance)
    stamp = _time(executed_at, evidence.lineage[0].executed_at)
    observation = evidence.observation
    checks = (
        _pass(
            "stored_artifact_integrity",
            "loaded_by_verified_store",
            "canonical_manifest_matches_local_artifact_hash",
            "Prerequisite verified by the calling artifact store before this operation.",
        ),
        _pass(
            "response_contract_at_ingestion",
            "contract_1.0.0_ingestion_evidence",
            "fixed_count_response_contract",
            "Retained ingestion evidence; original response bytes are not rechecked here.",
        ),
        _pass(
            "normalized_schema",
            "strict_model_valid",
            "count_and_provenance_contract_1.0.0",
            "Revalidated strict normalized types, source evidence and supported fields.",
        ),
        _pass(
            "normalization_lineage",
            "local_hashes_and_time_order_match",
            "input_response_hash_and_recomputed_normalized_hash_match_lineage",
            "Recomputed normalized-content hash and checked lineage references and time order.",
        ),
        _pass(
            "nonnegative_record_count",
            observation.record_count,
            "strict_integer_greater_than_or_equal_to_zero",
            "Zero is valid; a boolean, missing, suppressed or negative count is not zero.",
        ),
        _pass(
            "fixed_count_scope",
            "CA_primary_cardiology_record_count",
            "fixed_aggregate_not_distinct_people",
            "Only the saved California primary-cardiology aggregate is represented.",
        ),
        _not_checked("raw_response_rehash", "Original response bytes are not persisted."),
        _not_checked("publisher_integrity", "No verified publisher checksum is available."),
        _not_checked("raw_row_quality", "Individual source rows are not retrieved or inspected."),
        _not_checked("duplicates", "A single aggregate cannot assess duplicate source records."),
        _not_checked("null_patterns", "A single aggregate cannot assess source-row null patterns."),
        _not_checked(
            "immutable_release_binding", "The mutable datastore has no verified immutable binding."
        ),
    )
    return ValidationReport(
        artifact_id=artifact_id,
        source_ref=observation.source.source_ref,
        snapshot_id=observation.snapshot_id,
        scope=CountScope(synthetic=observation.source.synthetic),
        executed_at=stamp,
        overall="pass",
        checks=checks,
    )


def query_count(
    artifact_id: str,
    provenance: Provenance,
    validation_id: str,
    report: ValidationReport,
    request: QueryRequest,
    *,
    executed_at: datetime,
) -> QueryResult:
    """Project/filter one saved aggregate after a matching, passing validation report."""
    _id(artifact_id, "artifact")
    _id(validation_id, "validation")
    evidence = _provenance(provenance)
    checked_report = None
    try:
        checked_report = ValidationReport.model_validate(report)
    except (ValidationError, RecursionError):
        pass
    if checked_report is None:
        raise AnalyticsError("invalid_validation_report")
    if checked_report.overall != "pass":
        raise AnalyticsError("validation_failed")
    observation = evidence.observation
    if (
        checked_report.artifact_id != artifact_id
        or checked_report.source_ref != observation.source.source_ref
        or checked_report.snapshot_id != observation.snapshot_id
        or checked_report.scope != CountScope(synthetic=observation.source.synthetic)
    ):
        raise AnalyticsError("validation_scope_mismatch")
    expected = validate_count(artifact_id, evidence, executed_at=checked_report.executed_at)
    if checked_report != expected:
        raise AnalyticsError("invalid_validation_report")
    stamp = _time(executed_at, checked_report.executed_at)
    checked_request = None
    try:
        checked_request = QueryRequest.model_validate(request)
    except (ValidationError, RecursionError):
        pass
    if checked_request is None:
        raise AnalyticsError("invalid_query")
    _validate_query(checked_request)
    rows = _rows(checked_request, observation.record_count)
    return QueryResult(
        artifact_id=artifact_id,
        validation_id=validation_id,
        source_ref=observation.source.source_ref,
        snapshot_id=observation.snapshot_id,
        scope=expected.scope,
        request=checked_request,
        input_record_count=observation.record_count,
        normalization_executed_at=evidence.lineage[0].executed_at,
        validation_executed_at=checked_report.executed_at,
        columns=TypeAdapter(tuple[Column, ...]).validate_python(tuple(checked_request.select)),
        rows=rows,
        row_count=len(rows),
        executed_at=stamp,
    )


def render_csv(result: QueryResult) -> bytes:
    """Render only deep-validated allowed cells; caller owns bounded export publication."""
    checked = None
    try:
        checked = QueryResult.model_validate(result)
    except (ValidationError, RecursionError):
        pass
    if checked is None:
        raise AnalyticsError("invalid_query_result")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(checked.columns)
    writer.writerows(checked.rows)
    return output.getvalue().encode("utf-8")
