"""Offline application operations connecting count validation, lineage, and storage."""

from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

from cms_mcp.models import CountObservation, CountResponseError, Provenance, SourceReference
from cms_mcp.storage import ArtifactStoreError, LocalArtifactStore


class CountServiceError(ValueError):
    """Fixed code only; do not log payloads, exception locals, or Pydantic details."""


@dataclass(frozen=True)
class CountArtifact:
    """Service result with stored identity and its original immutable evidence."""

    artifact_id: str
    provenance: Provenance


class CountService:
    """Synthetic-only operations; no transport, network access, or implicit timestamps."""

    def __init__(self, store: LocalArtifactStore) -> None:
        self._store = store

    def materialize_count(
        self,
        body: bytes,
        *,
        source: SourceReference,
        retrieved_at: datetime,
        normalized_at: datetime,
    ) -> CountArtifact:
        """Validate and normalize before publishing; return only after storage succeeds."""
        error = "invalid_materialization"
        try:
            source = SourceReference.model_validate(source)
            if not source.synthetic:
                raise CountServiceError("synthetic_source_required")
            observation = CountObservation.from_response(
                body, source=source, retrieved_at=retrieved_at
            )
            provenance = Provenance.from_observation(observation, normalized_at=normalized_at)
            artifact_id = self._store.put(provenance)
            return CountArtifact(artifact_id=artifact_id, provenance=provenance)
        except (CountResponseError, ArtifactStoreError) as exc:
            error = str(exc)
        except ValidationError:
            pass
        # Raise after leaving handlers to detach errors that may retain input data.
        raise CountServiceError(error)

    def get_provenance(
        self, artifact_id: str, *, expected_source_ref: str, served_at: datetime
    ) -> Provenance:
        """Read an exact synthetic artifact with fresh service time and original lineage."""
        try:
            provenance = self._store.get(
                artifact_id, expected_source_ref=expected_source_ref, served_at=served_at
            )
            if not provenance.observation.source.synthetic:
                raise CountServiceError("synthetic_source_required")
            return provenance
        except ArtifactStoreError as exc:
            error = str(exc)
        raise CountServiceError(error)
