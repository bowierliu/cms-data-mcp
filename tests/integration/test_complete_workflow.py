"""The approved end-to-end aggregate workflow, offline by default."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from cms_mcp import service

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 4, 20, tzinfo=UTC)


def workflow(root):
    from cms_mcp.workflow import Workflow

    return Workflow(root, clock=lambda: NOW)


def test_discovery_metadata_schema_and_complete_csv_lineage(tmp_path):
    app = workflow(tmp_path)
    search = app.search("cardiologist specialty", limit=5)
    assert {row["dataset_id"] for row in search} == {"mj5m-pzi6", "synthetic-count-v1"}
    assert app.search("hospital infection", limit=5) == []
    metadata = app.metadata("synthetic-count-v1", "fixture-v1")
    source_ref = metadata.source_ref
    assert metadata.source.synthetic
    schema = app.schema("synthetic-count-v1", source_ref, ["record_count"])
    assert schema[0]["name"] == "record_count"
    created = app.retrieve("synthetic-count-v1", source_ref)
    artifact_id = created.artifact_id
    report_id, report = app.validate(artifact_id)
    assert report.overall == "pass"
    query_id, result = app.query(
        artifact_id,
        report_id,
        {
            "select": ["state", "record_count"],
            "filters": [],
            "limit": 1,
        },
    )
    assert result.row_count == 1
    export_id, exported, csv = app.export(query_id)
    assert csv == "state,record_count\r\nCA,5\r\n"
    assert exported.result_id == query_id
    assert len(list((tmp_path / "exports").glob("*.csv"))) == 1
    restarted = workflow(tmp_path)
    evidence = restarted.provenance(export_id)
    assert evidence["artifact_id"] == artifact_id
    assert evidence["provenance"].observation.record_count == 5
    assert [step["record_id"] for step in evidence["records"]] == [report_id, query_id, export_id]
    assert restarted.export(query_id)[0] == export_id
    assert restarted.provenance(source_ref)["source"].source_ref == source_ref


def test_live_is_opt_in_and_unknown_release_has_no_side_effects(tmp_path):
    from cms_mcp.workflow import WorkflowError

    app = workflow(tmp_path)
    with pytest.raises(WorkflowError, match="live_access_disabled"):
        app.metadata("mj5m-pzi6", "latest")
    with pytest.raises(WorkflowError, match="release_unresolved"):
        app.metadata("synthetic-count-v1", "2020-01")
    assert not list(tmp_path.iterdir())


def test_invalid_queries_do_not_publish_and_parent_corruption_blocks_export(tmp_path):
    from cms_mcp.analytics import AnalyticsError
    from cms_mcp.storage import ArtifactStoreError

    app = workflow(tmp_path)
    metadata = app.metadata("synthetic-count-v1", "fixture-v1")
    artifact = app.retrieve("synthetic-count-v1", metadata.source_ref)
    report_id, _ = app.validate(artifact.artifact_id)
    with pytest.raises(AnalyticsError, match="unsupported_geography"):
        app.query(artifact.artifact_id, report_id, {"select": ["county"]})
    assert not list((tmp_path / "records").glob("result-*.json"))
    query_id, _ = app.query(artifact.artifact_id, report_id, {})
    path = tmp_path / (artifact.artifact_id.split(":")[1] + ".json")
    path.write_bytes(b"corrupt")
    with pytest.raises(ArtifactStoreError, match="artifact_hash_mismatch"):
        app.export(query_id)
    assert not (tmp_path / "exports").exists()


def test_cross_fixture_count_and_forged_derived_parents_rejected(tmp_path):
    from cms_mcp.storage import LocalArtifactStore
    from cms_mcp.synthetic import load_synthetic_fixture
    from cms_mcp.workflow import WorkflowError

    fixture = load_synthetic_fixture()
    seeded = service.CountService(LocalArtifactStore(tmp_path)).materialize_count(
        json.dumps(json.loads(fixture.body) | {"count": 100}).encode(),
        source=fixture.source,
        retrieved_at=fixture.retrieved_at,
        normalized_at=fixture.normalized_at,
    )
    with pytest.raises(WorkflowError, match="source_scope_mismatch"):
        workflow(tmp_path).validate(seeded.artifact_id)


def test_derived_provenance_cannot_be_served_before_its_execution(tmp_path):
    from cms_mcp.workflow import Workflow, WorkflowError

    app = workflow(tmp_path)
    created = app.materialize_synthetic()
    report_id, _ = app.validate(created.artifact_id)
    result_id, _ = app.query(created.artifact_id, report_id, {})
    export_id, _, _ = app.export(result_id)
    past = Workflow(tmp_path, clock=lambda: NOW - timedelta(days=1))
    for identifier in (report_id, result_id, export_id):
        with pytest.raises(WorkflowError, match="invalid_operation_time"):
            past.provenance(identifier)
