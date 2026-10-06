"""Exercise real local files with synthetic count observations; no network."""

import errno
import hashlib
import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from threading import Barrier

import pytest

from cms_mcp import storage
from cms_mcp.models import CountObservation, Provenance, SourceReference, count_request
from cms_mcp.storage import ArtifactStoreError, LocalArtifactStore

pytestmark = pytest.mark.integration
RETRIEVED = datetime(2026, 10, 4, 12, tzinfo=UTC)
SERVED = RETRIEVED + timedelta(days=1)


@pytest.fixture
def provenance():
    source = SourceReference(
        distribution_id="11111111-2222-4333-8444-555555555555",
        download_url="https://data.cms.gov/provider-data/sites/default/files/resources/"
        "synthetic/DAC_NationalDownloadableFile.csv",
        catalog_released=None,
        catalog_modified=None,
        metadata_hash="a" * 64,
        checked_at=RETRIEVED - timedelta(seconds=1),
        synthetic=True,
    )
    query = count_request() | {"resources": [{"id": source.distribution_id, "alias": "t"}]}
    observation = CountObservation.from_response(
        json.dumps({"count": 7, "query": query}).encode(), source=source, retrieved_at=RETRIEVED
    )
    return Provenance.from_observation(observation, normalized_at=RETRIEVED)


def read(store, artifact_id, provenance, served_at=SERVED):
    return store.get(
        artifact_id,
        expected_source_ref=provenance.observation.source.source_ref,
        served_at=served_at,
    )


def artifact_path(root, artifact_id):
    return root / (artifact_id.removeprefix("artifact:") + ".json")


def install_bytes(root, body):
    root.mkdir(exist_ok=True)
    digest = hashlib.sha256(body).hexdigest()
    (root / f"{digest}.json").write_bytes(body)
    return f"artifact:{digest}"


def test_roundtrip_in_new_store_preserves_original_evidence(tmp_path, provenance):
    root = tmp_path / "cache"
    artifact_id = LocalArtifactStore(root).put(provenance)
    path = artifact_path(root, artifact_id)
    before = path.read_bytes()
    result = read(LocalArtifactStore(root), artifact_id, provenance)
    assert result.observation == provenance.observation
    assert result.observation.record_count == 7
    assert result.lineage == provenance.lineage
    assert result.observation.retrieved_at == RETRIEVED
    assert result.observation.source.checked_at == RETRIEVED - timedelta(seconds=1)
    assert result.served_at == SERVED
    assert result.cache_status == "hit"
    assert path.read_bytes() == before
    assert artifact_id == "artifact:" + hashlib.sha256(before).hexdigest()
    document = json.loads(before)
    assert document["format_version"] == 1
    assert document["provenance"]["cache_status"] == "not_served"
    assert set(document) == {"format_version", "provenance"}
    assert "query" not in document["provenance"]["observation"]
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def test_repeat_put_does_not_replace_existing_file(tmp_path, provenance):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    path = artifact_path(tmp_path, artifact_id)
    before = path.stat()
    assert store.put(provenance) == artifact_id
    after = path.stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert len(list(tmp_path.iterdir())) == 1


def test_concurrent_identical_writers_publish_one_complete_artifact(tmp_path, provenance):
    barrier = Barrier(6)

    def write():
        barrier.wait(timeout=10)
        return LocalArtifactStore(tmp_path).put(provenance)

    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(lambda _: write(), range(6)))
    assert len(set(ids)) == 1
    assert len(list(tmp_path.iterdir())) == 1
    assert read(LocalArtifactStore(tmp_path), ids[0], provenance).observation.record_count == 7


def test_corruption_is_rejected_and_never_silently_repaired(tmp_path, provenance):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    path = artifact_path(tmp_path, artifact_id)
    damaged = path.read_bytes().replace(b'"record_count":7', b'"record_count":8')
    path.write_bytes(damaged)
    with pytest.raises(ArtifactStoreError, match="artifact_hash_mismatch"):
        read(store, artifact_id, provenance)
    with pytest.raises(ArtifactStoreError):
        store.put(provenance)
    assert path.read_bytes() == damaged
    assert not list(tmp_path.glob(".pending-*"))


@pytest.mark.parametrize("change", ["state", "source", "version", "rows", "lineage", "served"])
def test_self_hashed_invalid_manifests_are_rejected(tmp_path, provenance, change):
    document = {"format_version": 1, "provenance": provenance.model_dump(mode="json")}
    observation = document["provenance"]["observation"]
    if change == "state":
        observation["state"] = "NY"
    elif change == "source":
        observation["source"]["source_id"] = "unapproved-dataset"
    elif change == "version":
        document["format_version"] = 2
    elif change == "rows":
        observation["results"] = [{"synthetic_secret": "DO_NOT_ECHO"}]
    elif change == "lineage":
        document["provenance"]["lineage"][0]["input_hash"] = "b" * 64
    else:
        document["provenance"] = provenance.served_from_cache(SERVED).model_dump(mode="json")
    body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    artifact_id = install_bytes(tmp_path, body)
    with pytest.raises(ArtifactStoreError) as caught:
        read(LocalArtifactStore(tmp_path), artifact_id, provenance)
    assert "DO_NOT_ECHO" not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


@pytest.mark.parametrize(
    "body",
    [
        b'{"synthetic_secret":"DO_NOT_ECHO",',
        b"DO_NOT_ECHO\xff",
        b"null",
        b'{"format_version":1,"format_version":2}',
        b'{"count":NaN}',
    ],
)
def test_invalid_json_errors_do_not_expose_contents(tmp_path, provenance, body):
    artifact_id = install_bytes(tmp_path, body)
    with pytest.raises(ArtifactStoreError) as caught:
        read(LocalArtifactStore(tmp_path), artifact_id, provenance)
    assert "DO_NOT_ECHO" not in str(caught.value)
    assert caught.value.__context__ is None


def test_duplicate_keys_and_noncanonical_valid_json_are_rejected(tmp_path, provenance):
    store = LocalArtifactStore(tmp_path)
    original = artifact_path(tmp_path, store.put(provenance)).read_bytes()
    for body in (
        b" " + original,
        original.replace(b'"format_version":1', b'"format_version":2,"format_version":1'),
    ):
        artifact_id = install_bytes(tmp_path, body)
        with pytest.raises(ArtifactStoreError, match="invalid_artifact"):
            read(store, artifact_id, provenance)


def test_expected_source_is_required_and_must_match(tmp_path, provenance):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    with pytest.raises(ArtifactStoreError, match="source_scope_mismatch"):
        store.get(artifact_id, expected_source_ref="source:" + "b" * 64, served_at=SERVED)


@pytest.mark.parametrize("change", ["metadata", "distribution", "synthetic", "retrieval"])
def test_different_evidence_never_reuses_artifact_identity(tmp_path, provenance, change):
    raw = provenance.observation.model_dump()
    if change == "metadata":
        raw["source"]["metadata_hash"] = "b" * 64
    elif change == "distribution":
        raw["source"]["distribution_id"] = "00000000-0000-4000-8000-000000000000"
    elif change == "synthetic":
        raw["source"]["synthetic"] = False
    else:
        raw["retrieved_at"] += timedelta(seconds=1)
    changed = Provenance.from_observation(
        CountObservation.model_validate(raw), normalized_at=RETRIEVED + timedelta(seconds=2)
    )
    store = LocalArtifactStore(tmp_path)
    original_id = store.put(provenance)
    changed_id = store.put(changed)
    assert changed_id != original_id
    assert read(store, changed_id, changed).observation == changed.observation
    if change != "retrieval":
        with pytest.raises(ArtifactStoreError, match="source_scope_mismatch"):
            read(store, original_id, changed)


@pytest.mark.parametrize(
    "artifact_id",
    ["../escape", "/tmp/outside", "artifact:" + "a" * 64 + "\n", "artifact:" + "A" * 64, "", None],
)
def test_invalid_artifact_ids_are_rejected_before_filesystem_access(
    tmp_path, provenance, artifact_id
):
    root = tmp_path / "not-created"
    with pytest.raises(ArtifactStoreError, match="invalid_artifact_id"):
        read(LocalArtifactStore(root), artifact_id, provenance)
    assert not root.exists()


def test_missing_artifact_is_explicit_and_does_not_create_root(tmp_path, provenance):
    root = tmp_path / "not-created"
    with pytest.raises(ArtifactStoreError, match="artifact_not_found"):
        read(LocalArtifactStore(root), "artifact:" + "a" * 64, provenance)
    assert not root.exists()


def test_oversized_read_and_write_fail_without_publishing(tmp_path, provenance):
    artifact_id = install_bytes(tmp_path, b"x" * (65536 + 1))
    with pytest.raises(ArtifactStoreError, match="artifact_too_large"):
        read(LocalArtifactStore(tmp_path), artifact_id, provenance)
    raw = provenance.observation.model_dump()
    raw["source"]["download_url"] = (
        "https://data.cms.gov/provider-data/sites/default/files/resources/"
        + "x" * 65536
        + "/DAC_NationalDownloadableFile.csv"
    )
    oversized = Provenance.from_observation(
        CountObservation.model_validate(raw), normalized_at=RETRIEVED
    )
    root = tmp_path / "new"
    with pytest.raises(ArtifactStoreError, match="artifact_too_large"):
        LocalArtifactStore(root).put(oversized)
    assert not root.exists()


def test_put_rejects_invalid_or_served_values_without_writes(tmp_path, provenance):
    root = tmp_path / "new"
    invalid = provenance.model_copy(update={"cache_status": "hit"})
    for value in (
        invalid,
        provenance.served_from_cache(SERVED),
        {"synthetic_secret": "DO_NOT_ECHO"},
    ):
        with pytest.raises(ArtifactStoreError) as caught:
            LocalArtifactStore(root).put(value)
        assert caught.value.__context__ is None
    assert not root.exists()


@pytest.mark.parametrize("timestamp", [datetime(2026, 10, 5), RETRIEVED - timedelta(seconds=1)])
def test_invalid_serving_times_cannot_change_stored_artifact(tmp_path, provenance, timestamp):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    before = artifact_path(tmp_path, artifact_id).read_bytes()
    with pytest.raises(ArtifactStoreError, match="invalid_serving_time"):
        read(store, artifact_id, provenance, timestamp)
    assert artifact_path(tmp_path, artifact_id).read_bytes() == before


@pytest.mark.parametrize("failure_at", ["file_sync", "publish", "directory_sync"])
def test_write_failures_never_expose_partial_artifacts(
    tmp_path, provenance, monkeypatch, failure_at
):
    store = LocalArtifactStore(tmp_path)
    real_fsync = storage.os.fsync
    real_link = storage.os.link

    def fsync(fd):
        is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if (failure_at == "directory_sync") == is_directory and failure_at != "publish":
            raise OSError("SYNTHETIC_PRIVATE_PATH")
        return real_fsync(fd)

    def link(*args, **kwargs):
        assert not list(tmp_path.glob("*.json"))
        if failure_at == "publish":
            raise OSError("SYNTHETIC_PRIVATE_PATH")
        return real_link(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(storage.os, "fsync", fsync)
        patch.setattr(storage.os, "link", link)
        with pytest.raises(ArtifactStoreError, match="storage_io_error") as caught:
            store.put(provenance)
        assert caught.value.__context__ is None
        assert "SYNTHETIC_PRIVATE_PATH" not in str(caught.value)
    assert not list(tmp_path.glob(".pending-*"))
    if failure_at != "directory_sync":
        assert not list(tmp_path.glob("*.json"))
    else:
        assert len(list(tmp_path.glob("*.json"))) == 1
    artifact_id = store.put(provenance)
    assert read(store, artifact_id, provenance).observation.record_count == 7


def test_symlink_root_is_not_followed(tmp_path, provenance):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "cache"
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ArtifactStoreError):
        LocalArtifactStore(root).put(provenance)
    assert not list(outside.iterdir())


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_nonregular_artifact_is_never_followed_or_replaced(tmp_path, provenance, kind):
    store = LocalArtifactStore(tmp_path / "cache")
    artifact_id = store.put(provenance)
    path = artifact_path(tmp_path / "cache", artifact_id)
    original = path.read_bytes()
    path.unlink()
    target = tmp_path / "outside.json"
    target.write_bytes(original)
    if kind == "symlink":
        path.symlink_to(target)
    elif kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    with pytest.raises(ArtifactStoreError):
        read(store, artifact_id, provenance)
    with pytest.raises(ArtifactStoreError):
        store.put(provenance)
    assert target.read_bytes() == original
    assert not list((tmp_path / "cache").glob(".pending-*"))


@pytest.mark.parametrize("operation", ["get", "put"])
def test_directory_artifact_rejection_closes_open_descriptor(
    tmp_path, provenance, monkeypatch, operation
):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    path = artifact_path(tmp_path, artifact_id)
    path.unlink()
    path.mkdir()
    opened = []
    real_open = storage.os.open

    def track_open(name, *args, **kwargs):
        fd = real_open(name, *args, **kwargs)
        if name == path.name:
            opened.append(fd)
        return fd

    monkeypatch.setattr(storage.os, "open", track_open)
    with pytest.raises(ArtifactStoreError):
        if operation == "get":
            read(store, artifact_id, provenance)
        else:
            store.put(provenance)
    assert opened
    for fd in opened:
        with pytest.raises(OSError) as caught:
            os.fstat(fd)
        assert caught.value.errno == errno.EBADF


def test_timestamp_overflow_in_manifest_is_reported_as_invalid_artifact(tmp_path, provenance):
    document = {"format_version": 1, "provenance": provenance.model_dump(mode="json")}
    document["provenance"]["observation"]["source"]["checked_at"] = "0001-01-01T00:00:00+01:00"
    artifact_id = install_bytes(
        tmp_path, json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    )
    with pytest.raises(ArtifactStoreError, match="invalid_artifact") as caught:
        read(LocalArtifactStore(tmp_path), artifact_id, provenance)
    assert caught.value.__context__ is None


def test_timestamp_overflow_when_serving_uses_fixed_error(tmp_path, provenance):
    store = LocalArtifactStore(tmp_path)
    artifact_id = store.put(provenance)
    timestamp = datetime(9999, 12, 31, 23, 59, tzinfo=timezone(-timedelta(hours=1)))
    with pytest.raises(ArtifactStoreError, match="invalid_serving_time") as caught:
        read(store, artifact_id, provenance, timestamp)
    assert caught.value.__context__ is None
