"""Typed derived records use the same immutable file safety as count artifacts."""

import hashlib
import json

import pytest

from cms_mcp import storage
from cms_mcp.models import SourceReference
from cms_mcp.synthetic import load_synthetic_fixture

pytestmark = pytest.mark.integration


def test_content_store_roundtrip_identity_idempotence_and_traversal(tmp_path):
    store_type = getattr(storage, "LocalContentStore", None)
    assert store_type is not None
    store = store_type(tmp_path)
    body = b"state,record_count\r\nCA,5\r\n"
    identifier = store.put_bytes("export", body, suffix=".csv")
    assert identifier == "export:" + hashlib.sha256(body).hexdigest()
    assert store.put_bytes("export", body, suffix=".csv") == identifier
    assert store.read_bytes(identifier, "export", suffix=".csv") == body
    assert len(list(tmp_path.iterdir())) == 1
    with pytest.raises(storage.ArtifactStoreError, match="invalid_export_id"):
        store.read_bytes("../../private", "export", suffix=".csv")


def test_content_store_rejects_corruption_symlinks_and_oversize(tmp_path):
    store_type = getattr(storage, "LocalContentStore", None)
    assert store_type is not None
    store = store_type(tmp_path / "records")
    identifier = store.put_bytes("result", b"{}")
    path = next((tmp_path / "records").iterdir())
    path.write_bytes(b"corrupt")
    for call in (
        lambda: store.read_bytes(identifier, "result"),
        lambda: store.put_bytes("result", b"{}"),
    ):
        with pytest.raises(storage.ArtifactStoreError, match="artifact_hash_mismatch"):
            call()
    path.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"{}")
    path.symlink_to(outside)
    with pytest.raises(storage.ArtifactStoreError):
        store.read_bytes(identifier, "result")
    assert outside.read_bytes() == b"{}"
    with pytest.raises(storage.ArtifactStoreError, match="artifact_too_large"):
        store.put_bytes("result", b"x" * (storage.MAX_ARTIFACT_BYTES + 1))


def test_typed_document_identity_matches_source_and_validates_schema(tmp_path):
    from cms_mcp.records import DocumentStore

    documents = DocumentStore(tmp_path)
    source = load_synthetic_fixture().source
    identifier = documents.put("source", source)
    assert identifier == source.source_ref
    assert documents.get(identifier, "source", SourceReference) == source
    malformed = source.model_dump(mode="json") | {"download_url": "https://invalid.example"}
    body = json.dumps(malformed, sort_keys=True, separators=(",", ":")).encode()
    identifier = storage.LocalContentStore(tmp_path).put_bytes("source", body)
    with pytest.raises(storage.ArtifactStoreError, match="invalid_artifact"):
        documents.get(identifier, "source", SourceReference)


def test_inspection_verifies_count_bytes_without_claiming_source_scope(tmp_path):
    from cms_mcp.models import CountObservation, Provenance

    fixture = load_synthetic_fixture()
    provenance = Provenance.from_observation(
        CountObservation.from_response(
            fixture.body, source=fixture.source, retrieved_at=fixture.retrieved_at
        ),
        normalized_at=fixture.normalized_at,
    )
    store = storage.LocalArtifactStore(tmp_path)
    identifier = store.put(provenance)
    assert hasattr(store, "inspect")
    assert store.inspect(identifier) == provenance
    assert store.inspect(identifier).served_at is None
