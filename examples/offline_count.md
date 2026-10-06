# Run the offline count workflow

Run these commands from the `cms-data-mcp` project root after `uv sync --locked --group dev`.

```bash
uv run python -m cms_mcp.demo
```

The command loads a packaged synthetic response, validates the fixed California/
primary-cardiology count, records provenance, saves an immutable artifact, opens
a fresh service/store, and retrieves the provenance. It prints one JSON document.
No CMS request is made. The default temporary artifact is removed before exit.

To retain the artifact for inspection or repeat runs:

```bash
uv run python -m cms_mcp.demo --cache-dir data/cache/offline-demo
```

Expected key output values:

```json
{
  "synthetic": true,
  "fixture_id": "synthetic-count-v1",
  "storage": "persistent",
  "record_count": 5,
  "counts_distinct_people": false
}
```

The actual output also contains the artifact, source, snapshot, stored-provenance,
and served-provenance IDs plus the complete returned provenance. The count is
fictional and refers to enrollment/location records, not unique clinicians.
The embedded CMS-shaped URL is a synthetic placeholder and is never fetched.

The fixed fixture's acquisition time is `2026-01-01T00:00:01Z`; its normalization
time is one second later. Cache reads add the actual serving time. Running the
command again keeps the same stored artifact and acquisition evidence, while the
served-provenance ID changes with service time. The artifact filename is its
SHA-256 digest followed by `.json`; cache contents are ignored by Git.

Runtime failures return a fixed JSON error on stderr and a nonzero exit code.
CLI argument/help errors use standard argparse behavior. For example, selecting
a regular file as `--cache-dir` fails with `storage_io_error` without overwriting
it. Corrupted existing artifacts fail rather than being silently repaired.

This is an application/CLI demo. An AI agent cannot call it through MCP yet.
General queries, city/county filtering, exports, and live retrieval remain planned.
See the [application contract](../docs/offline-workflow.md).
