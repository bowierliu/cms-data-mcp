"""Typed public tool contracts and dispatch, independent of the MCP wire transport."""

from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from cms_mcp.analytics import QueryRequest, QueryResult, ValidationReport
from cms_mcp.models import SPECIALTY, Provenance, SourceReference
from cms_mcp.workflow import ExportRecord, Metadata, Workflow

ArtifactID = Annotated[str, Field(pattern=r"^artifact:[0-9a-f]{64}$", min_length=73, max_length=73)]
SourceID = Annotated[str, Field(pattern=r"^source:[0-9a-f]{64}$", min_length=71, max_length=71)]
ValidationID = Annotated[
    str, Field(pattern=r"^validation:[0-9a-f]{64}$", min_length=75, max_length=75)
]
ResultID = Annotated[str, Field(pattern=r"^result:[0-9a-f]{64}$", min_length=71, max_length=71)]
ReferenceID = Annotated[
    str, Field(pattern=r"^(artifact|source|validation|result|export):[0-9a-f]{64}$", max_length=75)
]


class Model(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class Empty(Model):
    pass


class SearchInput(Model):
    query: Annotated[str, Field(min_length=1, max_length=200)]
    limit: Annotated[int, Field(ge=1, le=20)] = 5


class MetadataInput(Model):
    dataset_id: Annotated[str, Field(min_length=1, max_length=64)]
    release: Annotated[str, Field(min_length=1, max_length=64)] = "latest"


class SchemaInput(Model):
    dataset_id: Annotated[str, Field(min_length=1, max_length=64)]
    source_ref: SourceID
    fields: (
        Annotated[
            list[Annotated[str, Field(min_length=1, max_length=64)]],
            Field(min_length=1, max_length=20),
        ]
        | None
    ) = None


class RetrievalInput(Model):
    dataset_id: Annotated[str, Field(min_length=1, max_length=64)]
    source_ref: SourceID
    view: Literal["california_primary_cardiology_record_count"] = (
        "california_primary_cardiology_record_count"
    )
    cached_artifact_id: ArtifactID | None = None


class ArtifactInput(Model):
    artifact_id: ArtifactID


class QueryInput(QueryRequest):
    artifact_id: ArtifactID
    validation_id: ValidationID


class ExportInput(Model):
    result_id: ResultID
    format: Literal["csv"] = "csv"


class ProvenanceInput(Model):
    artifact_id: ReferenceID


class Scope(Model):
    dataset_id: str | None = None
    source_id: Literal["cms-pdc:mj5m-pzi6"] = "cms-pdc:mj5m-pzi6"
    synthetic: bool | None = None
    fixture_id: Literal["synthetic-count-v1"] | None = None
    state: Literal["CA"] | None = None
    primary_specialty: str | None = None
    count_unit: Literal["enrollment_location_records"] = "enrollment_location_records"
    completeness: Literal["curated_catalog", "metadata_only", "complete_for_fixed_aggregate_view"]
    truncated: bool = False


Data = TypeVar("Data")


class Envelope(Model, Generic[Data]):
    summary: str
    data: Data
    scope: Scope
    warnings: list[str]
    provenance_id: ReferenceID | None


class ToolError(Model):
    code: str
    message: str
    recovery: str


class ErrorEnvelope(Model):
    error: ToolError


class SearchData(Model):
    datasets: list[dict[str, Any]]
    total_matches: Annotated[int, Field(ge=0, le=2)]
    catalog_scope: Literal["one_curated_CMS_source_and_its_synthetic_fixture"] = (
        "one_curated_CMS_source_and_its_synthetic_fixture"
    )


class MetadataData(Model):
    source_ref: SourceID
    metadata: Metadata


class SchemaData(Model):
    source_ref: SourceID
    fields: list[dict[str, Any]]
    schema_basis: Literal["curated_dictionary_mapping_reviewed_2026-10-02"] = (
        "curated_dictionary_mapping_reviewed_2026-10-02"
    )


class ArtifactData(Model):
    artifact_id: ArtifactID
    source_ref: SourceID
    snapshot_id: str
    record_count: Annotated[int, Field(ge=0)]
    counts_distinct_people: Literal[False] = False
    cache_status: Literal["not_served", "hit"]


class ValidationData(Model):
    validation_id: ValidationID
    report: ValidationReport


class QueryData(Model):
    result_id: ResultID
    result: QueryResult


class ExportData(Model):
    export_id: ReferenceID
    export: ExportRecord
    content: Annotated[str, Field(max_length=65_536)]


class Evidence(Model):
    record_id: ReferenceID
    record: ValidationReport | QueryResult | ExportRecord


class ProvenanceData(Model):
    source: SourceReference
    source_ref: SourceID
    artifact_id: ArtifactID | None = None
    snapshot_id: str | None = None
    record_count: int | None = None
    counts_distinct_people: Literal[False] = False
    provenance: Provenance | None = None
    records: list[Evidence]


@dataclass(frozen=True)
class ToolContract:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    writes: bool = False
    network: bool = False
    idempotent: bool = True

    def output_schema(self) -> dict[str, Any]:
        # Keep shared definitions at the root so both anyOf branches resolve refs.
        schema = TypeAdapter(self.output_model | ErrorEnvelope).json_schema()
        return {"type": "object", **schema}


CONTRACTS = [
    ToolContract(
        "search_datasets",
        "Search the curated CMS clinician-specialty source and its fictional fixture. "
        "Not a search of all CMS datasets. No network.",
        SearchInput,
        Envelope[SearchData],
    ),
    ToolContract(
        "get_dataset_metadata",
        "Resolve source evidence and save a source_ref before schema/retrieval. Use "
        "synthetic-count-v1 offline; mj5m-pzi6 requires operator-enabled live access. "
        "Only latest, or fixture-v1 for synthetic. Catalog release is not an immutable "
        "datastore version.",
        MetadataInput,
        Envelope[MetadataData],
        True,
        True,
        False,
    ),
    ToolContract(
        "get_schema",
        "Explain selected fields from the reviewed dictionary mapping. Normalized query"
        " fields: state, primary_specialty, record_count. Source-only metadata fields: "
        "npi, pri_spec, citytown, zip_code (case-sensitive). No personal values or "
        "county support. Pass dataset_id and "
        "source_ref from metadata.",
        SchemaInput,
        Envelope[SchemaData],
    ),
    ToolContract(
        "retrieve_dataset",
        "Save only the fixed California primary-cardiology record count. Pass "
        "dataset_id/source_ref from metadata. Optional cached_artifact_id reuses "
        "exactly that source without network. No rows, expanded filters, URLs, or "
        "historical release binding.",
        RetrievalInput,
        Envelope[ArtifactData],
        True,
        True,
        False,
    ),
    ToolContract(
        "materialize_synthetic_count",
        "Create the packaged fictional five-record count without arguments/network. "
        "Returns artifact_id for validation or provenance. Never report it as real CMS "
        "data.",
        Empty,
        Envelope[ArtifactData],
        True,
    ),
    ToolContract(
        "validate_dataset",
        "Verify a saved count artifact and persist an explicit validation report. Pass "
        "artifact_id; returns validation_id required by query_dataset. Raw dataset "
        "quality and publisher integrity stay not_checked.",
        ArtifactInput,
        Envelope[ValidationData],
        True,
        False,
        False,
    ),
    ToolContract(
        "query_dataset",
        "Project/filter the one saved aggregate row after validation. Requires "
        "artifact_id and matching validation_id. Fields: state, primary_specialty, "
        "record_count; eq for text, eq/gte/lte for count. No upstream narrowing, city, "
        "county, SQL, grouping, or distinct-person counts. Empty results are valid.",
        QueryInput,
        Envelope[QueryData],
        True,
        False,
        False,
    ),
    ToolContract(
        "export_result",
        "Write the exact saved query result as bounded CSV under the server-owned "
        "export directory. Pass result_id; returns CSV text, hash, export_id and "
        "lineage reference. No caller path or re-query.",
        ExportInput,
        Envelope[ExportData],
        True,
        False,
        False,
    ),
    ToolContract(
        "get_provenance",
        "Read source evidence and ordered validation/query/export lineage without "
        "writes. Put any returned provenance_id "
        "(source/artifact/validation/result/export ID) in artifact_id. Preserves "
        "acquisition times; adds serving time. No latest lookup or network.",
        ProvenanceInput,
        Envelope[ProvenanceData],
    ),
]


def response(
    summary: str,
    data: BaseModel,
    source: SourceReference | None,
    reference: str | None,
    *,
    metadata_only: bool = False,
    truncated: bool = False,
) -> Envelope[Any]:
    warnings = [
        "Counts represent enrollment/location records, not distinct clinicians.",
        "Publisher integrity and underlying dataset quality were not assessed.",
    ]
    if source is not None and source.synthetic:
        warnings.insert(0, "Synthetic fixture only; fictional data, not CMS observations.")
    elif source is not None:
        warnings.append("Mutable datastore observation; no verified immutable release binding.")
    scope = Scope(
        dataset_id=None
        if source is None
        else ("synthetic-count-v1" if source.synthetic else "mj5m-pzi6"),
        synthetic=source.synthetic if source else None,
        fixture_id="synthetic-count-v1" if source and source.synthetic else None,
        state="CA" if source and not metadata_only else None,
        primary_specialty=SPECIALTY if source and not metadata_only else None,
        completeness="curated_catalog"
        if source is None
        else ("metadata_only" if metadata_only else "complete_for_fixed_aggregate_view"),
        truncated=truncated,
    )
    return Envelope[Any](
        summary=summary, data=data, scope=scope, warnings=warnings, provenance_id=reference
    )


def invoke(app: Workflow, name: str, arguments: BaseModel) -> Envelope[Any]:
    if isinstance(arguments, SearchInput):
        matches = app.search(arguments.query, limit=20)
        return response(
            "Curated candidates; use metadata to resolve source evidence.",
            SearchData(datasets=matches[: arguments.limit], total_matches=len(matches)),
            None,
            None,
            truncated=len(matches) > arguments.limit,
        )
    if isinstance(arguments, MetadataInput):
        metadata = app.metadata(arguments.dataset_id, arguments.release)
        return response(
            "Selected source evidence; immutable release remains unknown.",
            MetadataData(source_ref=metadata.source_ref, metadata=metadata),
            metadata.source,
            metadata.source_ref,
            metadata_only=True,
        )
    if isinstance(arguments, SchemaInput):
        fields = app.schema(arguments.dataset_id, arguments.source_ref, arguments.fields)
        source = app.provenance(arguments.source_ref)["source"]
        return response(
            "Reviewed field meanings; only three normalized fields are queryable.",
            SchemaData(source_ref=arguments.source_ref, fields=fields),
            source,
            arguments.source_ref,
            metadata_only=True,
        )
    if isinstance(arguments, (Empty, RetrievalInput)):
        created = (
            app.materialize_synthetic()
            if isinstance(arguments, Empty)
            else app.retrieve(
                arguments.dataset_id, arguments.source_ref, arguments.cached_artifact_id
            )
        )
        observation = created.provenance.observation
        return response(
            "Validated and stored the fixed aggregate count.",
            ArtifactData(
                artifact_id=created.artifact_id,
                source_ref=observation.source.source_ref,
                snapshot_id=observation.snapshot_id,
                record_count=observation.record_count,
                cache_status=created.provenance.cache_status,
            ),
            observation.source,
            created.artifact_id,
        )
    if isinstance(arguments, ArtifactInput):
        identifier, report = app.validate(arguments.artifact_id)
        source = app.provenance(arguments.artifact_id)["source"]
        return response(
            "Required count-contract checks passed; unchecked assessments listed.",
            ValidationData(validation_id=identifier, report=report),
            source,
            identifier,
        )
    if isinstance(arguments, QueryInput):
        identifier, result = app.query(
            arguments.artifact_id,
            arguments.validation_id,
            arguments.model_dump(exclude={"artifact_id", "validation_id"}),
        )
        source = app.provenance(arguments.artifact_id)["source"]
        return response(
            "Saved a constrained result over the original aggregate view.",
            QueryData(result_id=identifier, result=result),
            source,
            identifier,
        )
    if isinstance(arguments, ExportInput):
        identifier, record, content = app.export(arguments.result_id)
        source = app.provenance(record.artifact_id)["source"]
        return response(
            "Exported exactly the saved result, with unchanged scope.",
            ExportData(export_id=identifier, export=record, content=content),
            source,
            identifier,
        )
    if isinstance(arguments, ProvenanceInput):
        evidence = app.provenance(arguments.artifact_id)
        return response(
            "Verified source and parent records; original evidence preserved.",
            ProvenanceData(**evidence),
            evidence["source"],
            arguments.artifact_id,
            metadata_only=arguments.artifact_id.startswith("source:"),
        )
    raise ValueError("unknown_tool")
