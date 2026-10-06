"""Application and subprocess workflow checks using only synthetic local data."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from importlib.resources import files

import pytest

from cms_mcp.models import CountObservation, Provenance, SourceReference
from cms_mcp.service import CountService, CountServiceError
from cms_mcp.storage import LocalArtifactStore

pytestmark = pytest.mark.integration
SERVED = datetime(2026, 10, 4, 12, tzinfo=UTC)


@pytest.fixture
def inputs():
    fixture = json.loads(files("cms_mcp").joinpath("fixtures/synthetic-count-v1.json").read_text())
    metadata = fixture["metadata"]
    metadata_hash = hashlib.sha256(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    source = SourceReference.model_validate_json(
        json.dumps(
            {
                **metadata,
                "metadata_hash": metadata_hash,
                "checked_at": fixture["checked_at"],
                "synthetic": True,
            }
        )
    )
    return {
        "body": json.dumps(fixture["response"], sort_keys=True, separators=(",", ":")).encode(),
        "source": source,
        "retrieved_at": datetime.fromisoformat(fixture["retrieved_at"]),
        "normalized_at": datetime.fromisoformat(fixture["normalized_at"]),
    }


def test_materialize_and_lookup_across_service_instances(tmp_path, inputs):
    result = CountService(LocalArtifactStore(tmp_path)).materialize_count(**inputs)
    assert result.provenance.observation.record_count == 5
    assert result.provenance.observation.source.synthetic is True
    assert result.provenance.cache_status == "not_served"
    assert result.provenance.observation.response_hash == hashlib.sha256(inputs["body"]).hexdigest()
    assert len(list(tmp_path.glob("*.json"))) == 1
    saved = next(tmp_path.glob("*.json")).read_bytes()
    recovered = CountService(LocalArtifactStore(tmp_path)).get_provenance(
        result.artifact_id, expected_source_ref=inputs["source"].source_ref, served_at=SERVED
    )
    assert recovered.observation == result.provenance.observation
    assert recovered.lineage == result.provenance.lineage
    assert recovered.served_at == SERVED
    assert recovered.cache_status == "hit"
    assert next(tmp_path.glob("*.json")).read_bytes() == saved
    assert "results" not in json.loads(saved)["provenance"]["observation"]


def test_materialization_is_repeatable(tmp_path, inputs):
    service = CountService(LocalArtifactStore(tmp_path))
    first = service.materialize_count(**inputs)
    assert service.materialize_count(**inputs) == first
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("failure", ["rows", "query", "count", "json", "source", "time", "naive"])
def test_invalid_materialization_never_publishes(tmp_path, inputs, failure):
    payload = json.loads(inputs["body"])
    if failure == "rows":
        payload["results"] = [{"synthetic_secret": "DO_NOT_ECHO"}]
    elif failure == "query":
        payload["query"]["conditions"][0]["value"] = "NY"
    elif failure == "count":
        payload["count"] = True
    elif failure == "source":
        inputs["source"] = inputs["source"].model_copy(update={"metadata_hash": "DO_NOT_ECHO"})
    elif failure == "time":
        inputs["normalized_at"] = inputs["retrieved_at"] - timedelta(seconds=1)
    elif failure == "naive":
        inputs["retrieved_at"] = datetime(2026, 1, 1)
    inputs["body"] = b'{"DO_NOT_ECHO":' if failure == "json" else json.dumps(payload).encode()
    root = tmp_path / "cache"
    with pytest.raises(CountServiceError) as caught:
        CountService(LocalArtifactStore(root)).materialize_count(**inputs)
    assert "DO_NOT_ECHO" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert not root.exists()


def test_service_rejects_nonsynthetic_materialization_and_lookup(tmp_path, inputs):
    inputs["source"] = SourceReference.model_validate(
        inputs["source"].model_dump() | {"synthetic": False}
    )
    service = CountService(LocalArtifactStore(tmp_path))
    with pytest.raises(CountServiceError, match="synthetic_source_required"):
        service.materialize_count(**inputs)
    # An independently seeded lower-level store cannot bypass the service boundary.
    observation = CountObservation.from_response(
        inputs["body"], source=inputs["source"], retrieved_at=inputs["retrieved_at"]
    )
    provenance = Provenance.from_observation(observation, normalized_at=inputs["normalized_at"])
    artifact_id = LocalArtifactStore(tmp_path).put(provenance)
    with pytest.raises(CountServiceError, match="synthetic_source_required"):
        service.get_provenance(
            artifact_id, expected_source_ref=inputs["source"].source_ref, served_at=SERVED
        )


@pytest.mark.parametrize("failure", ["missing", "scope", "corrupt", "time", "path"])
def test_lookup_failures_are_explicit_and_preserve_artifacts(tmp_path, inputs, failure):
    service = CountService(LocalArtifactStore(tmp_path))
    result = service.materialize_count(**inputs)
    artifact_id = result.artifact_id
    source_ref = inputs["source"].source_ref
    served_at = SERVED
    path = next(tmp_path.glob("*.json"))
    codes = {
        "missing": "artifact_not_found",
        "scope": "source_scope_mismatch",
        "corrupt": "artifact_hash_mismatch",
        "time": "invalid_serving_time",
        "path": "invalid_artifact_id",
    }
    if failure == "missing":
        artifact_id = "artifact:" + "0" * 64
    elif failure == "scope":
        source_ref = "source:" + "b" * 64
    elif failure == "corrupt":
        path.write_bytes(b"DO_NOT_ECHO")
    elif failure == "time":
        served_at = datetime(2026, 1, 1)
    else:
        artifact_id = "../DO_NOT_ECHO"
    before = path.read_bytes()
    with pytest.raises(CountServiceError, match=codes[failure]) as caught:
        service.get_provenance(artifact_id, expected_source_ref=source_ref, served_at=served_at)
    assert caught.value.__context__ is None
    assert path.read_bytes() == before


def test_storage_failure_is_not_reported_as_materialization_success(tmp_path, inputs):
    root = tmp_path / "DO_NOT_ECHO"
    root.write_text("existing file")
    with pytest.raises(CountServiceError, match="storage_io_error") as caught:
        CountService(LocalArtifactStore(root)).materialize_count(**inputs)
    assert caught.value.__context__ is None
    assert root.read_text() == "existing file"


def run_demo(cwd, *args, temp_root=None):
    return subprocess.run(
        [sys.executable, "-I", "-m", "cms_mcp.demo", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=os.environ | ({"TMPDIR": str(temp_root)} if temp_root is not None else {}),
    )


def test_default_demo_is_offline_labeled_and_temporary(tmp_path):
    temp_root = tmp_path / "system-tmp"
    temp_root.mkdir()
    result = run_demo(tmp_path, temp_root=temp_root)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    output = json.loads(result.stdout)
    assert output["synthetic"] is True
    assert output["fixture_id"] == "synthetic-count-v1"
    assert output["storage"] == "temporary_removed_on_exit"
    assert output["record_count"] == 5
    assert output["counts_distinct_people"] is False
    assert output["provenance"]["cache_status"] == "hit"
    assert not list(temp_root.iterdir())
    assert list(tmp_path.iterdir()) == [temp_root]


def test_demo_persistent_rerun_reuses_artifact_and_preserves_evidence(tmp_path):
    root = tmp_path / "cache"
    first = run_demo(tmp_path, "--cache-dir", str(root))
    assert first.returncode == 0, first.stderr
    before = next(root.glob("*.json")).read_bytes()
    second = run_demo(tmp_path, "--cache-dir", str(root))
    assert second.returncode == 0, second.stderr
    one, two = json.loads(first.stdout), json.loads(second.stdout)
    assert two["storage"] == "persistent"
    for field in ("artifact_id", "source_ref", "snapshot_id", "stored_provenance_id"):
        assert one[field] == two[field]
    assert two["provenance"]["observation"]["retrieved_at"] == "2026-01-01T00:00:01Z"
    assert next(root.glob("*.json")).read_bytes() == before
    assert len(list(root.iterdir())) == 1


def test_demo_errors_are_json_without_tracebacks_or_success_output(tmp_path):
    root = tmp_path / "DO_NOT_ECHO"
    root.write_text("existing file")
    result = run_demo(tmp_path, "--cache-dir", str(root))
    assert result.returncode == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {"error": "storage_io_error", "synthetic": True}
    assert "DO_NOT_ECHO" not in result.stderr
