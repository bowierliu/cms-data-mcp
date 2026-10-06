"""Immutable typed source, validation, query, and export records."""

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from cms_mcp.storage import ArtifactStoreError, LocalContentStore

Record = TypeVar("Record", bound=BaseModel)


def encode(record: BaseModel) -> bytes:
    return json.dumps(
        record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


class DocumentStore:
    def __init__(self, root: Path) -> None:
        self._files = LocalContentStore(root)

    def put(self, kind: str, record: BaseModel) -> str:
        return self._files.put_bytes(kind, encode(record))

    def get(self, identifier: str, kind: str, model: type[Record]) -> Record:
        body = self._files.read_bytes(identifier, kind)
        record = None
        try:
            parsed = model.model_validate_json(body)
            if encode(parsed) == body:
                record = parsed
        except (ValueError, RecursionError):
            pass
        if record is None:
            raise ArtifactStoreError("invalid_artifact")
        return record
