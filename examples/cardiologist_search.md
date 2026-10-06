# Working cardiology-count walkthrough

Run `uv run python scripts/check_mcp.py` from the project root for the complete
synthetic workflow. Add `--live --cache-dir data/cache/live-demo` for the approved
CMS observation. [Detailed demo](../docs/demo.md).

1. Search the curated catalog for clinician specialty information.
2. Resolve `synthetic-count-v1` metadata (or `mj5m-pzi6` with live access enabled).
3. Inspect `state`, `primary_specialty`, and `record_count` field definitions.
4. Retrieve the fixed California/primary-cardiology count using `source_ref`.
5. Validate the artifact and pass its `validation_id` into `query_dataset`.
6. Select `state` and `record_count`; export the saved result as CSV.
7. Inspect the export's provenance reference to see source, times, checks and
   ordered query/export records.

The synthetic output is one row, CA / 5 fictional enrollment/location records.
The earlier city-level CSV fixture is not wired into this workflow. No county
result or distinct-clinician count can be inferred. A San Diego County request
returns `UNSUPPORTED_GEOGRAPHY`; the system does not substitute city or ZIP.
