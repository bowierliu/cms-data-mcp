# Local storage verification — 2026-10-04

Implemented `LocalArtifactStore` for the [bounded storage contract](storage-contract.md).
No network requests or new dependencies were needed. All observations are
synthetic; test artifacts live in temporary directories.

Environment: local macOS, Python 3.11.15, Pydantic 2.13.5, existing `uv.lock`.

```bash
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache pytest -q
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff format --check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache mypy src scripts
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache python scripts/verify_scaffold.py
uv build --offline --cache-dir /tmp/cms-data-mcp-uv-cache
```

Results: 86 tests passed (43 model tests, 43 real-filesystem integration cases),
lint/format passed, strict mypy passed for five source/script files, scaffold/link
validation passed, and sdist/wheel builds passed. The first test run failed
collection because `storage.py` did not yet exist.

The installed wheel was replaced in the isolated temporary verification venv
using offline `uv pip install --no-deps --reinstall-package cms-data-mcp`; its
previously installed dependencies were retained. From `/tmp`, Python `-I`
successfully persisted synthetic provenance, reopened the store, and recovered
the count as a cache hit with original retrieval time. This verifies installed
package behavior, not a fresh offline dependency installation.

Integration coverage includes independent-store round-trips, hash identity,
idempotent and concurrent publication, corrupted bytes, self-hashed invalid
manifests, duplicate keys, unknown formats, forbidden rows, source mismatches,
file bounds, path traversal, symlinks, directories, FIFOs, safe errors, and
failures at file fsync, publication, and directory fsync. Existing files are never
silently replaced or repaired. Post-publication failures may leave a complete,
readable file; retry succeeds without overwriting it.

Independent review found a descriptor leak on directory targets and unhandled
UTC overflow at the model validation boundary. Four regression cases failed
before correction, then passed; the reviewer independently confirmed the fixes
with no outstanding findings in scope.

Untested/deferred: Windows and network filesystems, power-loss durability,
hostile local writers, hard process-death cleanup, generic cache freshness,
SDK/stdio integration, live CMS transport, and agent evals. The store checks local
manifest integrity; it cannot recheck upstream response bytes that it does not
retain and does not assert publisher authorship or underlying dataset quality.
