---
name: provenance
description: Use when designing or auditing lineage for retrieved, cached, normalized, queried, validated, or exported CMS artifacts.
---

# Provenance

Every meaningful result must identify its inputs, evidence, and transformations.
Read the canonical record contract in `docs/provenance.md` before changing fields.

Capture source publisher, dataset name/ID, landing and distribution URLs, resolved
release or explicitly labeled snapshot identity, release evidence, coverage
period, retrieval timestamp, requested scope, completeness, byte hash with origin,
and validation state. Record software/contract versions and stable artifact IDs.
Use timezone-aware UTC times; unknown evidence remains null with a reason.

Keep transformations ordered and append-only. Each operation identifies inputs,
validated parameters, output artifact/hash, implementation version, and execution
time. Derived results retain their source lineage. Validation reports reference
the artifact and contract actually checked, not whatever happens to be latest.

Example: serving cached bytes today preserves yesterday's `retrieved_at`. Add
`served_at` and `cache_status=hit`. Update `checked_at` only for an actual source
check and describe that check. Retain the old filter/normalization steps before
appending the new query. A local SHA-256 has origin `local`; it cannot stand in
for an absent publisher checksum.

Distinguish a live paginated extract from an immutable release: record requests,
page times, and snapshot limitations. If the source can change between pages,
do not certify an atomic snapshot. Include projection, filters, and limits in
cache identity. Export must link back to its result and original inputs.

Return the lineage record and its evidence gaps. Avoid storing credentials,
signed secret URLs, or personal row payloads in provenance. A compact MCP response
may carry a provenance ID, but that ID must resolve to the complete allowed record.
