"""Packaged fictional count input shared by offline application adapters."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files

from cms_mcp.models import SourceReference

FIXTURE_ID = "synthetic-count-v1"


@dataclass(frozen=True)
class SyntheticCountFixture:
    source: SourceReference
    body: bytes
    retrieved_at: datetime
    normalized_at: datetime


def load_synthetic_fixture() -> SyntheticCountFixture:
    """Read trusted packaged data; no external URL or file input is supported."""
    fixture = json.loads(files("cms_mcp").joinpath(f"fixtures/{FIXTURE_ID}.json").read_text())
    if fixture["fixture_id"] != FIXTURE_ID or fixture["synthetic"] is not True:
        raise ValueError("invalid_fixture")
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
    return SyntheticCountFixture(
        source=source,
        body=json.dumps(fixture["response"], sort_keys=True, separators=(",", ":")).encode(),
        retrieved_at=datetime.fromisoformat(fixture["retrieved_at"]),
        normalized_at=datetime.fromisoformat(fixture["normalized_at"]),
    )
