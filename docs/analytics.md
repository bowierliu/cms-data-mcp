# Fixed-count validation, query, and CSV contracts

`analytics.py` operates on one saved aggregate: the number of California
enrollment/location records with primary specialty `CARDIOVASCULAR DISEASE
(CARDIOLOGY)`. The aggregate is one result row regardless of whether its count
is zero, five, or another nonnegative integer. It never counts distinct people,
includes secondary-specialty matches, or infers city/county/ZIP membership.
The source's synthetic flag remains attached to every derived record.

## Validation reports

`validate_count(artifact_id, provenance, executed_at=...)` is a pure operation.
Its caller must first load the artifact through the verified immutable store;
the report explicitly labels stored-artifact integrity as that prerequisite.
This function revalidates the strict normalized model, local normalization hash,
lineage references, time order, nonnegative count, and fixed aggregate scope.
It records the response contract checked at ingestion as retained evidence.
It cannot repeat original-response validation because those bytes are not saved.

Each report binds the artifact ID, source reference, snapshot ID, scope, UTC
execution time, operation name, and implementation/contract versions. Every
check has an ID, severity, required flag, observed value, expected condition,
status, and explanation. All six required checks must pass for overall `pass`.
Missing/duplicate checks, inconsistent overall results, and invented passes for
unsupported assessments fail deserialization.

The six unchecked assessments are original-response rehashing, publisher
integrity, source-row quality, duplicates, null patterns, and immutable-release
binding. Passing this report says that the stored fixed aggregate satisfies
its local contract; it does not certify the entire source dataset.

Reports are persisted and assigned `validation:<sha256>` IDs by the application
workflow, outside this pure module. Corrupt storage and invalid normalized
evidence are rejected before a valid report can be produced.

## Constrained query requests

`QueryRequest` accepts only:

| Field | Supported values |
| --- | --- |
| `select` | One to three distinct names from `state`, `primary_specialty`, `record_count`; defaults to all three |
| `filters` | Zero to three `{field, op, value}` objects, combined with AND |
| `limit` | Strict integer from 1 through 100; defaults to 100 |

`eq` accepts an uppercase two-letter code for the 50 US states, DC, or AS/GU/MP/PR/VI
when the field is `state`. For `primary_specialty`, it accepts only the exact
approved `CARDIOVASCULAR DISEASE (CARDIOLOGY)` label. These finite categories keep
arbitrary caller text out of saved query requests, including empty results.
The `record_count` field accepts an integer comparison value. `gte` and `lte`
apply only to the integer count. Booleans,
numeric strings in count comparisons, unknown operators/fields, arbitrary
SQL, extra arguments, and duplicate projection columns are rejected.
County/city/ZIP and related geography requests return `unsupported_geography`.
Field names are at most 64 characters; filter strings are at most 128.

Filters evaluate the saved aggregate row locally. For example, `state eq NY`
returns no rows because the saved row describes California. It never retrieves
a New York count. The aggregate count itself is not recomputed by a filter.
All allowed limits can contain the entire one-row view, so `truncated` is false.

`query_count(...)` requires a passing report whose artifact, source, snapshot,
scope, checks, and observed values match the supplied provenance. It rechecks
the report against deterministic validation at the report's original timestamp.
Validation cannot precede normalization; query execution cannot precede
validation. These timestamps describe processing, not new source retrieval.

## Saved result and CSV

`QueryResult` binds its artifact and validation IDs, source/snapshot identities,
scope, exact request, input count, processing timestamps, versions and operation
`query_fixed_count`. `columns` is an ordered tuple and `rows` is a tuple of
ordered tuples aligned with those columns. JSON serializes both as arrays.
There are zero or one rows. The saved input count permits reconstruction even
when the projection omits `record_count` or filters yield an empty result.

Deserialization recomputes the expected rows from the request and input count;
it rejects changed column order, unsupported values, inconsistent row counts,
forged filter results, and incorrect time order. The application additionally
checks that the input count and parent references match the current verified
artifact and validation report; local structural validity alone is not proof
that a parent exists or remains intact.

`render_csv(result)` revalidates the complete result and returns UTF-8 CSV bytes
with CRLF line endings and the exact selected header order. An empty query
produces a header-only CSV. Cells can contain only validated constant state and
specialty strings or a nonnegative integer. Caller-supplied filter text is
never written into cells. The renderer accepts no path and writes no files;
the application owns bounded, immutable publication under the operator's export
directory and preserves links to the query and original evidence.

## Verification boundary

The offline unit tests cover local filtering, zero and empty results, strict
types/limits, unsupported geography, failed/mismatched reports, ordering of
times, and forged persisted results or CSV values. Application and MCP tests
separately exercise persistence, parent verification, transport, and exports.
No test in this module contacts CMS or reads individual source records.
