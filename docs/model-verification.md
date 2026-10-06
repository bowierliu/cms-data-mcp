# Domain model verification — 2026-10-03

Scope: offline `SourceReference`, `CountObservation`, and `Provenance` models for
the verified fixed California/primary-cardiology record count. No live CMS calls
were made for this implementation. Runtime dependencies were fetched from PyPI.

Environment: Python 3.11.15, Pydantic 2.13.5; dependencies recorded in `uv.lock`.
Commands run from the `cms-data-mcp` root, using the temporary uv cache:

```bash
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache pytest -q
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff format --check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache mypy src scripts
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache python scripts/verify_scaffold.py
uv build --offline --cache-dir /tmp/cms-data-mcp-uv-cache
```

Results: 43 tests passed; lint, formatting, strict typing, scaffold/link checks,
and source/wheel builds passed. These checks do not imply a working MCP server,
live adapter, persistent cache, or agent evaluation harness.

Installed the built wheel into a separate temporary virtual environment and ran
Python with `-I` from `/tmp`. Imports, synthetic count parsing, provenance JSON
round-trip, and the packaged `py.typed` marker passed. Offline dependency
resolution for that separate environment initially failed despite the populated
cache; allowing normal PyPI resolution completed installation. This is a package
smoke check, not a claim that fresh installation works without cached dependencies.

Tests cover unknown publisher release identity, strict nonnegative counts,
query/resource drift, forbidden rows, malformed/duplicate/non-finite JSON,
response caps, optional schema compatibility, local byte hashes and identities,
timezone handling, immutable nested models, serialization, and cache provenance.
The first run failed collection because the new module did not yet exist.

Independent review found that `raise ... from None` retained a parser exception
containing rejected input. Two new regression cases failed before the correction.
Raising outside the handler removed that context; the reviewer independently
reran all 43 tests and confirmed the fix with no remaining findings in scope.

The full planned provenance/report schema is not implemented. The current API
supports one normalization step, metadata for cache serving, and JSON model
round-trips. It does not verify CMS authorship from a local hash or validate
underlying clinician records. General transformations remain deferred.
