# cms-data-mcp provenance contract

The fixed workflow implements source evidence, count identity, normalization,
validation, query, CSV export and cache serving metadata. [Typed models](model-contracts.md)
describe acquisition; [analytics](analytics.md) describes derived records. The
[local store](storage-contract.md) persists immutable count manifests; typed
source/report/result/export documents and CSV bytes extend that same bounded
atomic file mechanism. General transformations outside this workflow are deferred.

| Group | Required evidence |
| --- | --- |
| Identity | `provenance_id`, `artifact_id`, record schema version, synthetic flag |
| Source | Publisher, dataset name/ID, official landing URL, requested and resolved distribution URLs, documentation URL |
| Version | Requested selector, resolved release/snapshot identity, release evidence, publication time and coverage period if supplied |
| Time | `retrieved_at` UTC; separate `checked_at` for a documented source check and `served_at` for a cache response |
| Scope | Projection/view, filters, pagination, limits, returned count, completeness, source-consistency limitations |
| Integrity | Algorithm, local content hash, optional publisher checksum and its evidence, comparison status |
| Processing | Ordered operations, typed parameters, input/output artifact IDs and hashes, code/contract version, operation time |
| Validation | Report ID, artifact hash checked, contract version, check statuses and overall required-check result |
| Storage | Cache identity, hit/miss/revalidated status, local artifact reference; no secret or arbitrary path exposure |

Unknown upstream facts remain null with a reason. `latest` cannot be the final
artifact's sole version. If the source offers only a mutable endpoint, create a
snapshot identity based on observed bytes/scope/time and clearly label it as
local, not a publisher release. Live pagination may span upstream updates; report
that limitation rather than implying an atomic snapshot.

Metadata's `source_ref` binds an evidenced source selection, not retrieved bytes.
Keep it in the lineage. Its publisher release ID may be null. Retrieval produces
the local `snapshot_id` after acquisition; both identifiers remain distinct.

A SHA-256 computed locally proves which bytes were used. It does not independently
verify the publisher. Preserve whether a digest is local or publisher-supplied.
An unavailable publisher checksum is an explicit unchecked comparison.

On a cache hit, retain retrieval time and source lineage; add service time and
cache status. Append query/normalization/export operations without overwriting
their predecessors. Each derived artifact points to its parents. Include extract
scope in cache identity so a 50-row sample cannot satisfy a full-data request.

Validation checks use `pass`, `fail`, `warning`, and `not_checked`. An overall
report fails if a required check fails; queries cannot silently bypass that
failure. A complete report can still describe a deliberately partial extract.

Expose a compact provenance summary on every meaningful tool response and a
resolvable full record through `get_provenance`. Logs contain IDs, durations,
counts, and outcomes, never real personal rows or credentials.

MCP `provenance_id` is the source/artifact/validation/result/export reference for
that operation. Pass it as `get_provenance.artifact_id`. The lookup verifies all
parent files, repeats deterministic report/query checks, validates CSV bytes, and
returns ordered records. Serving cannot precede any referenced processing step.
The original application-only demo's `provenance:<hash>` values identify record
content; they are not entries in a generic provenance index.
