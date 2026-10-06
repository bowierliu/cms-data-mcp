"""Complete fixed-count workflow; typed records retain verified parent evidence."""

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cms_mcp.analytics import (
    QueryRequest,
    QueryResult,
    ValidationReport,
    query_count,
    render_csv,
    validate_count,
)
from cms_mcp.catalog import DATASET_IDS, DICTIONARY_URL, FIELDS, LANDING_URL, search_catalog
from cms_mcp.models import CountObservation, Provenance, SourceReference, Timestamp
from cms_mcp.records import DocumentStore
from cms_mcp.service import CountArtifact
from cms_mcp.sources import CMSClient
from cms_mcp.storage import LocalArtifactStore, LocalContentStore
from cms_mcp.synthetic import SyntheticCountFixture, load_synthetic_fixture

ID = Annotated[str, Field(pattern=r"^[a-z]+:[0-9a-f]{64}$", max_length=75)]


class WorkflowError(ValueError):
    """Fixed safe codes; no payloads attached."""


class Metadata(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    dataset_id: str
    source: SourceReference
    title: str
    publisher: str
    landing_url: str | None
    dictionary_url: str
    requested_release: str
    resolved_release_id: None = None
    coverage_start: None = None
    coverage_end: None = None

    @property
    def source_ref(self) -> str:
        return self.source.source_ref


class ExportRecord(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    result_id: ID
    file_id: ID
    artifact_id: ID
    byte_count: Annotated[int, Field(ge=0, le=65_536)]
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    row_count: Annotated[int, Field(ge=0, le=1)]
    executed_at: Timestamp
    operation: Literal["export_csv"] = "export_csv"
    format: Literal["csv"] = "csv"
    mime_type: Literal["text/csv"] = "text/csv"
    truncated: Literal[False] = False
    implementation_version: Literal["0.0.1"] = "0.0.1"
    contract_version: Literal["1.0.0"] = "1.0.0"

    @model_validator(mode="after")
    def identities(self) -> "ExportRecord":
        if (
            not self.result_id.startswith("result:")
            or not self.artifact_id.startswith("artifact:")
            or self.file_id != "export:" + self.sha256
        ):
            raise ValueError("invalid_export_identity")
        return self


class Workflow:
    def __init__(
        self,
        root: Path,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        enable_live: bool = False,
        client: CMSClient | None = None,
        fixture: SyntheticCountFixture | None = None,
    ) -> None:
        self.clock = clock
        self.enable_live = enable_live
        self.client = client or CMSClient(clock=clock)
        self.fixture = fixture or load_synthetic_fixture()
        self.expected = Provenance.from_observation(
            CountObservation.from_response(
                self.fixture.body,
                source=self.fixture.source,
                retrieved_at=self.fixture.retrieved_at,
            ),
            normalized_at=self.fixture.normalized_at,
        )
        self.artifacts = LocalArtifactStore(root)
        self.documents = DocumentStore(root / "records")
        self.exports = LocalContentStore(root / "exports")

    @staticmethod
    def _dataset(dataset_id: str) -> None:
        if dataset_id not in DATASET_IDS:
            raise WorkflowError("dataset_not_found")

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        if type(query) is not str or not 1 <= len(query.strip()) <= 200 or not 1 <= limit <= 20:
            raise WorkflowError("invalid_arguments")
        return search_catalog(query, limit)

    def metadata(self, dataset_id: str, release: str = "latest") -> Metadata:
        self._dataset(dataset_id)
        synthetic = dataset_id == "synthetic-count-v1"
        if release not in ({"latest", "fixture-v1"} if synthetic else {"latest"}):
            raise WorkflowError("release_unresolved")
        if not synthetic and not self.enable_live:
            raise WorkflowError("live_access_disabled")
        source = self.fixture.source if synthetic else self.client.metadata()
        self.documents.put("source", source)
        return Metadata(
            dataset_id=dataset_id,
            source=source,
            title="Fictional fixed cardiology count" if synthetic else "National Downloadable File",
            publisher="cms-data-mcp synthetic fixture"
            if synthetic
            else "Centers for Medicare & Medicaid Services (CMS)",
            landing_url=None if synthetic else LANDING_URL,
            dictionary_url=DICTIONARY_URL,
            requested_release=release,
        )

    def _source(self, dataset_id: str, source_ref: str) -> SourceReference:
        self._dataset(dataset_id)
        source = self.documents.get(source_ref, "source", SourceReference)
        if source.synthetic != (dataset_id == "synthetic-count-v1"):
            raise WorkflowError("source_scope_mismatch")
        if source.synthetic and source != self.fixture.source:
            raise WorkflowError("source_scope_mismatch")
        return source

    def schema(
        self, dataset_id: str, source_ref: str, fields: list[str] | None
    ) -> list[dict[str, Any]]:
        self._source(dataset_id, source_ref)
        selected = fields if fields is not None else ["state", "primary_specialty", "record_count"]
        if not 1 <= len(selected) <= 20 or len(set(selected)) != len(selected):
            raise WorkflowError("invalid_arguments")
        result = []
        for name in selected:
            if "county" in name.lower() or name.lower() == "city":
                raise WorkflowError("unsupported_geography")
            if name not in FIELDS:
                raise WorkflowError("unsupported_field")
            kind, description, queryable = FIELDS[name]
            result.append(
                {
                    "name": name,
                    "type": kind,
                    "description": description,
                    "queryable": queryable,
                    "evidence_url": DICTIONARY_URL,
                    "dictionary_reviewed_on": "2026-10-02",
                }
            )
        return result

    def materialize_synthetic(self) -> CountArtifact:
        identifier = self.artifacts.put(self.expected)
        return CountArtifact(identifier, self.expected)

    def retrieve(
        self, dataset_id: str, source_ref: str, cached_artifact_id: str | None = None
    ) -> CountArtifact:
        source = self._source(dataset_id, source_ref)
        if cached_artifact_id is not None:
            provenance = self._artifact(cached_artifact_id)
            if provenance.observation.source != source:
                raise WorkflowError("source_scope_mismatch")
            return CountArtifact(cached_artifact_id, provenance.served_from_cache(self.clock()))
        if source.synthetic:
            return self.materialize_synthetic()
        if not self.enable_live:
            raise WorkflowError("live_access_disabled")
        provenance = self.client.retrieve(source)
        return CountArtifact(self.artifacts.put(provenance), provenance)

    def _artifact(self, artifact_id: str) -> Provenance:
        provenance = self.artifacts.inspect(artifact_id)
        if provenance.observation.source.synthetic and provenance != self.expected:
            raise WorkflowError("source_scope_mismatch")
        return provenance

    def validate(self, artifact_id: str) -> tuple[str, ValidationReport]:
        report = validate_count(artifact_id, self._artifact(artifact_id), executed_at=self.clock())
        return self.documents.put("validation", report), report

    def _report(self, validation_id: str) -> tuple[ValidationReport, Provenance]:
        report = self.documents.get(validation_id, "validation", ValidationReport)
        provenance = self._artifact(report.artifact_id)
        expected = validate_count(report.artifact_id, provenance, executed_at=report.executed_at)
        if report != expected:
            raise WorkflowError("lineage_mismatch")
        return report, provenance

    def query(
        self, artifact_id: str, validation_id: str, request: dict[str, Any]
    ) -> tuple[str, QueryResult]:
        parsed = QueryRequest.model_validate_json(json.dumps(request))
        report, provenance = self._report(validation_id)
        result = query_count(
            artifact_id, provenance, validation_id, report, parsed, executed_at=self.clock()
        )
        return self.documents.put("result", result), result

    def _result(self, result_id: str) -> tuple[QueryResult, ValidationReport, Provenance]:
        result = self.documents.get(result_id, "result", QueryResult)
        report, provenance = self._report(result.validation_id)
        expected = query_count(
            result.artifact_id,
            provenance,
            result.validation_id,
            report,
            result.request,
            executed_at=result.executed_at,
        )
        if result != expected:
            raise WorkflowError("lineage_mismatch")
        return result, report, provenance

    def export(self, result_id: str) -> tuple[str, ExportRecord, str]:
        result, _, _ = self._result(result_id)
        body = render_csv(result)
        record = ExportRecord(
            result_id=result_id,
            file_id="export:" + hashlib.sha256(body).hexdigest(),
            artifact_id=result.artifact_id,
            byte_count=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            row_count=result.row_count,
            executed_at=self.clock(),
        )
        if record.executed_at < result.executed_at:
            raise WorkflowError("invalid_operation_time")
        self.exports.put_bytes("export", body, suffix=".csv")
        return self.documents.put("export", record), record, body.decode()

    def provenance(self, identifier: str) -> dict[str, Any]:
        kind = identifier.split(":", 1)[0]
        records: list[dict[str, Any]] = []
        if kind == "source":
            source = self.documents.get(identifier, "source", SourceReference)
            self._source("synthetic-count-v1" if source.synthetic else "mj5m-pzi6", identifier)
            return {"source": source, "source_ref": identifier, "records": records}
        if kind == "export":
            exported = self.documents.get(identifier, "export", ExportRecord)
            result, report, provenance = self._result(exported.result_id)
            body = self.exports.read_bytes(exported.file_id, "export", suffix=".csv")
            if (
                body != render_csv(result)
                or len(body) != exported.byte_count
                or exported.artifact_id != result.artifact_id
                or exported.row_count != result.row_count
                or exported.executed_at < result.executed_at
            ):
                raise WorkflowError("lineage_mismatch")
            records.append({"record_id": identifier, "record": exported})
            identifier, kind = exported.result_id, "result"
        if kind == "result":
            result, report, provenance = self._result(identifier)
            records.insert(0, {"record_id": identifier, "record": result})
            identifier, kind = result.validation_id, "validation"
        if kind == "validation":
            report, provenance = self._report(identifier)
            records.insert(0, {"record_id": identifier, "record": report})
            identifier, kind = report.artifact_id, "artifact"
        if kind != "artifact":
            raise WorkflowError("invalid_arguments")
        provenance = self._artifact(identifier).served_from_cache(self.clock())
        if any(provenance.served_at < step["record"].executed_at for step in records):
            raise WorkflowError("invalid_operation_time")
        return {
            "artifact_id": identifier,
            "source": provenance.observation.source,
            "source_ref": provenance.observation.source.source_ref,
            "snapshot_id": provenance.observation.snapshot_id,
            "record_count": provenance.observation.record_count,
            "counts_distinct_people": False,
            "provenance": provenance,
            "records": records,
        }
