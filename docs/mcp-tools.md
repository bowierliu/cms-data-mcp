# Implemented MCP tool contracts

Nine tools are available over local stdio. Eight form the primary workflow;
`materialize_synthetic_count` preserves the original offline shortcut.

| Tool | Inputs | Output / side effect |
| --- | --- | --- |
| `search_datasets` | `query` (1–200 characters), `limit` (1–20, default 5) | Curated candidates, total matches, truthful truncation; no I/O |
| `get_dataset_metadata` | `dataset_id`, `release` (default `latest`) | Saved source evidence and `source_ref`; live CMS requires startup flag |
| `get_schema` | `dataset_id`, `source_ref`, optional `fields` (1–20 unique names) | Reviewed field meanings, evidence URL and queryability; no live request |
| `retrieve_dataset` | `dataset_id`, `source_ref`, fixed `view`, optional `cached_artifact_id` | Saved aggregate identity/count/scope, or exact source-matched cached copy |
| `materialize_synthetic_count` | `{}` only | Idempotently stores packaged fictional count 5 |
| `validate_dataset` | `artifact_id` | Saved `validation_id` and explicit report |
| `query_dataset` | `artifact_id`, `validation_id`, optional `select`, `filters`, `limit` | Saved `result_id`, columns, zero/one rows, request and source scope |
| `export_result` | `result_id`, `format` (only `csv`) | Saved export manifest and CSV, content, hash, `export_id` |
| `get_provenance` | `artifact_id` accepting any returned source/artifact/validation/result/export reference | Verified original provenance plus ordered derived records; no writes |

Supported dataset IDs: `mj5m-pzi6` and `synthetic-count-v1`. The latter accepts
`latest` or `fixture-v1`; the live source accepts only `latest`. Live metadata
resolves current catalog evidence, with an explicitly unknown immutable release
identity. It never resolves a future update date as an available release.

The fixed retrieval view is `california_primary_cardiology_record_count`. It
cannot express new upstream predicates. `cached_artifact_id` preserves original
acquisition evidence and must match the selected source exactly. No implicit
latest cache policy or freshness claim is made.

## Example query

Use IDs returned by retrieval and validation:

```json
{
  "artifact_id": "artifact:<returned digest>",
  "validation_id": "validation:<returned digest>",
  "select": ["state", "record_count"],
  "filters": [{"field": "record_count", "op": "gte", "value": 0}],
  "limit": 1
}
```

These symbolic IDs must be replaced with real tool results. The synthetic row
is `["CA", 5]`. A `state eq NY` filter returns no rows because the saved aggregate
is California-only. It does not query New York upstream. Text filters use finite
approved categories, preventing arbitrary caller text from entering saved records.
See [analytics](analytics.md) for detailed bounds and interpretation.

## Responses, errors, and lineage

Success envelopes contain `summary`, `data`, `scope`, `warnings`, and
`provenance_id`. Except for unsaved catalog search, `provenance_id` is a resolvable
record reference. Pass it in `get_provenance.artifact_id`; despite the legacy
parameter name, it accepts source/report/result/export IDs too. The original
application-only CLI's provenance hashes remain content identities, not this
MCP lookup interface.

Data models and tool arguments are strict. Successful JSON is capped at 16 KiB,
returned as both structured content and equivalent text. Oversized responses fail
with `RESOURCE_LIMIT`. Each stored record is bounded to 64 KiB. Catalog search
reports truncation when its limit excludes a matching candidate; the complete
aggregate view itself always fits in one query row.

Every advertised output schema has an object root and an `anyOf` union of the
tool's success envelope and the shared typed error envelope. Both branches reject
additional properties. Tool failures retain `is_error=true` (`isError` on the wire)
and return `{"error":{"code":"...","message":"...","recovery":"..."}}` as both
structured content and equivalent text. The schema covers errors even when a
client validates them despite `isError`; success fields are not required on errors.
Regression tests explicitly validate both outcomes against the advertised schema,
rather than relying on the SDK's success-only output validation.

Tool failures use fixed code, explanation, and recovery.
Codes include `INVALID_ARGUMENTS`, `ARTIFACT_NOT_FOUND`, `ARTIFACT_CORRUPT`,
`SOURCE_SCOPE_MISMATCH`, `DATASET_NOT_FOUND`, `RELEASE_UNRESOLVED`,
`LIVE_ACCESS_DISABLED`, `UNSUPPORTED_GEOGRAPHY`, `UNSUPPORTED_FIELD`,
`VALIDATION_FAILED`, `SOURCE_CHANGED`, `SOURCE_CONTRACT_FAILED`,
`SOURCE_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `RESOURCE_LIMIT`, and `INTERNAL_ERROR`.
Unknown tool names produce protocol invalid-parameter errors. Adapter errors do
not reflect rejected input or filesystem paths. SDK protocol errors/debug logging
are outside that sanitization guarantee.

Annotations distinguish reads from writes and live-capable operations. Validation,
query and export persist timestamped derived records and do not claim idempotence.
The synthetic shortcut is idempotent. Read-only provenance refreshes serving time
without modifying stored evidence. Every derived lookup rechecks its parents;
a corrupted parent blocks export/provenance instead of silently trusting a child.

Grouping, Parquet export, general retrieval filters, arbitrary SQL, comparison,
and county enrichment remain future changes requiring new contracts and tests.
