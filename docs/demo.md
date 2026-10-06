# Reproducible first-release demo

## Offline example

```bash
uv sync --locked --group dev
uv run python scripts/check_mcp.py --cache-dir data/cache/offline-demo
```

The real SDK client follows the advertised workflow and prints a concise JSON
summary. Expected: `synthetic: true`, `record_count: 5`, `validation_status: pass`,
`query_rows: [["CA", 5]]`, CSV `state,record_count` followed by `CA,5`, and three
derived lineage steps (validation, query, export). The earlier normalization step
remains in the original provenance record.

## Permitted live example

```bash
uv run python scripts/check_mcp.py --live --cache-dir data/cache/live-demo
```

This verifies current CMS metadata, checks it again around the fixed count-only
request, validates the result and follows the same query/export/lineage workflow.
The 2026-10-04 run returned 5,634 records. A later run may differ and will retain its
own source evidence and retrieval time. It never downloads the raw clinician file.

CSV bytes are under the chosen root's `exports/`; immutable source/report/query/
export records are under `records/`. The summary supplies their IDs. The server
accepts no caller-selected export path. A run without `--cache-dir` uses temporary
storage and deletes it on exit.

## Explain the result in an interview

The AI agent chooses tools. Typed code restricts the source and request, verifies
responses, assigns local content identities, and persists immutable evidence.
Validation distinguishes checks performed from unavailable assurances. Queries
operate on the exact saved aggregate. Export preserves that result; provenance
rechecks every parent rather than trusting a copied description.

The count is enrollment/location records, not unique clinicians. The catalog's
release date is separate from mutable datastore acquisition. Local hashes are not
publisher checksums. County, city and personal-row analysis are unsupported.

[Setup](../examples/mcp_stdio.md) · [verification](release-verification.md) ·
[architecture](architecture.md) · [resume evidence](resume.md).
