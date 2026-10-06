"""Immutable, bounded count artifacts on a trusted local POSIX filesystem."""

import hashlib
import json
import os
import re
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from cms_mcp.models import Provenance

MAX_ARTIFACT_BYTES = 65_536


class ArtifactStoreError(ValueError):
    """Fixed code only; callers must not log untrusted content or traceback locals."""


class _Manifest(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    format_version: Literal[1] = 1
    provenance: Provenance

    @model_validator(mode="after")
    def _unserved(self) -> Self:
        if self.provenance.served_at is not None or self.provenance.cache_status != "not_served":
            raise ValueError("only_unserved_provenance_can_be_stored")
        return self


def _encode(manifest: _Manifest) -> bytes:
    return json.dumps(
        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _identifier(value: str, prefix: str) -> str:
    if not isinstance(value, str) or re.fullmatch(prefix + r":[0-9a-f]{64}", value) is None:
        raise ArtifactStoreError(f"invalid_{prefix}_id")
    return value[len(prefix) + 1 :]


def _decode(body: bytes) -> _Manifest:
    try:
        manifest = _Manifest.model_validate_json(body)
        canonical = _encode(manifest) == body
    except (ValueError, RecursionError):
        manifest = None
        canonical = False
    # Raise outside handlers: Pydantic/JSON exceptions may retain rejected data.
    if manifest is None or not canonical:
        raise ArtifactStoreError("invalid_artifact")
    return manifest


def _read(directory_fd: int, name: str) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode):
            raise ArtifactStoreError("invalid_artifact_file")
        if details.st_size > MAX_ARTIFACT_BYTES:
            raise ArtifactStoreError("artifact_too_large")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            body = handle.read(MAX_ARTIFACT_BYTES + 1)
    finally:
        os.close(fd)
    if len(body) > MAX_ARTIFACT_BYTES:
        raise ArtifactStoreError("artifact_too_large")
    return body


class LocalContentStore:
    """Bounded content-addressed files under a trusted operator-configured root."""

    def __init__(self, root: Path) -> None:
        self._root = root.absolute()

    @contextmanager
    def _directory(self, *, create: bool) -> Iterator[int]:
        if create:
            self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            yield fd
        finally:
            os.close(fd)

    @staticmethod
    def _name(prefix: str, digest: str, suffix: str) -> str:
        if prefix not in {"source", "validation", "result", "export", "provenance"}:
            raise ArtifactStoreError("invalid_record_kind")
        if suffix not in {".json", ".csv"}:
            raise ArtifactStoreError("invalid_record_format")
        return f"{prefix}-{digest}{suffix}"

    def put_bytes(self, prefix: str, body: bytes, *, suffix: str = ".json") -> str:
        if type(body) is not bytes or len(body) > MAX_ARTIFACT_BYTES:
            raise ArtifactStoreError("artifact_too_large")
        digest = _digest(body)
        name = self._name(prefix, digest, suffix)
        try:
            with self._directory(create=True) as directory_fd:
                self._publish(directory_fd, name, body)
            return f"{prefix}:{digest}"
        except OSError:
            pass
        raise ArtifactStoreError("storage_io_error")

    def read_bytes(self, identifier: str, prefix: str, *, suffix: str = ".json") -> bytes:
        name = self._name(prefix, _identifier(identifier, prefix), suffix)
        body = None
        error = "storage_io_error"
        try:
            with self._directory(create=False) as directory_fd:
                body = _read(directory_fd, name)
        except FileNotFoundError:
            error = "artifact_not_found"
        except OSError:
            pass
        if body is None:
            raise ArtifactStoreError(error)
        if _digest(body) != identifier.split(":", 1)[1]:
            raise ArtifactStoreError("artifact_hash_mismatch")
        return body

    @staticmethod
    def _publish(directory_fd: int, name: str, body: bytes) -> None:
        temporary = f".pending-{uuid4().hex}"
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        try:
            try:
                with os.fdopen(fd, "wb", closefd=False) as handle:
                    handle.write(body)
                    handle.flush()
                    os.fsync(handle.fileno())
            finally:
                os.close(fd)
            exists = False
            try:
                os.link(
                    temporary,
                    name,
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                exists = True
            if exists and _read(directory_fd, name) != body:
                raise ArtifactStoreError("artifact_hash_mismatch")
        finally:
            os.unlink(temporary, dir_fd=directory_fd)
        # Both publication and temp cleanup are durable before success is reported.
        os.fsync(directory_fd)


class LocalArtifactStore(LocalContentStore):
    """Store validated normalized counts and provenance, never raw responses."""

    def put(self, provenance: Provenance) -> str:
        """Publish atomically without replacing existing files; identical puts are idempotent."""
        manifest = None
        try:
            if isinstance(provenance, Provenance):
                manifest = _Manifest(provenance=provenance)
                body = _encode(manifest)
        except (ValueError, RecursionError):
            manifest = None
        if manifest is None:
            raise ArtifactStoreError("invalid_provenance")
        if len(body) > MAX_ARTIFACT_BYTES:
            raise ArtifactStoreError("artifact_too_large")
        digest = _digest(body)
        try:
            with self._directory(create=True) as directory_fd:
                self._publish(directory_fd, f"{digest}.json", body)
            return f"artifact:{digest}"
        except OSError:
            pass
        raise ArtifactStoreError("storage_io_error")

    def inspect(self, artifact_id: str) -> Provenance:
        """Verify bytes/model; the caller must separately enforce its allowed source scope."""
        digest = _identifier(artifact_id, "artifact")
        body = None
        error = "storage_io_error"
        try:
            with self._directory(create=False) as directory_fd:
                body = _read(directory_fd, f"{digest}.json")
        except FileNotFoundError:
            error = "artifact_not_found"
        except OSError:
            pass
        if body is None:
            raise ArtifactStoreError(error)
        if _digest(body) != digest:
            raise ArtifactStoreError("artifact_hash_mismatch")
        return _decode(body).provenance

    def get(self, artifact_id: str, *, expected_source_ref: str, served_at: datetime) -> Provenance:
        """Verify identity/scope and return a served copy, leaving stored evidence unchanged."""
        _identifier(artifact_id, "artifact")
        _identifier(expected_source_ref, "source")
        provenance = self.inspect(artifact_id)
        if provenance.observation.source.source_ref != expected_source_ref:
            raise ArtifactStoreError("source_scope_mismatch")
        try:
            return provenance.served_from_cache(served_at)
        except ValidationError:
            pass
        raise ArtifactStoreError("invalid_serving_time")
