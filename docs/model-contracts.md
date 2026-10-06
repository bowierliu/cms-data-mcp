# Typed domain models

This bounded implementation follows source contract `mj5m-pzi6` version 1.0.0.
It adds offline Python models, not network retrieval, caching, or MCP tools.

- `SourceReference` records metadata identity, catalog dates, a local metadata
  hash, and the actual check time. Its content-derived ID does not freeze the
  live datastore. The immutable publisher release ID remains null with a reason.
- `CountObservation.from_response` accepts bounded response bytes, a source
  reference, and retrieval time. It rejects coercible counts, unexpected rows,
  changed predicates, projections, resource IDs, and ambiguous JSON. Its local
  snapshot ID binds response bytes, source, fixed scope, and retrieval time.
- `Provenance.from_observation` records the normalization step, local hash
  origin, and narrowly scoped validation outcome. Cache serving returns a new
  record with a later serving time, preserving source, snapshot, and lineage.

Pydantic 2 supplies strict, frozen, extra-field-forbidden value models; nested
values use models and tuples, not mutable payload dictionaries. Aware timestamps
normalize to UTC. Use validated constructors/deserialization; Pydantic's explicit
validation bypass APIs are not trust boundaries. Raw response errors contain
fixed codes, never input rows. Callers must not log rejected payloads or raw
Pydantic error details. Hashes prove local byte identity, not CMS authorship.
`source_ref`, `snapshot_id`, and `provenance_id` are derived Python properties,
recomputed from validated content after a JSON round-trip, not serialized fields.
`from_observation` requires an explicit `normalized_at` timestamp; it must follow
retrieval. Deserializing a normalized observation checks its shape, while verifying
its recorded response hash still requires the original permitted response bytes.

Only the approved state/primary-specialty count is supported. A successful
response check does not validate underlying records or establish an immutable
publisher release. Optional schema checks cover resource identity and required
filter field types; they are not full source quality validation. Transformation
support is limited to one normalization step; arbitrary derived operations and
generic derived operations belong to later work. The separate
[storage module](storage-contract.md) now persists this model subset.

## Execution and acceptance

1. Add and lock Pydantic; write offline tests before implementation.
2. Implement the three models and safe count-response parsing.
3. Test unknown releases, query/resource drift, count types, unexpected rows,
   malformed JSON, hashes, timezone handling, serialization, and cache times.
4. Independently review the boundary, run tests/lint/type/package checks, and
   update project state and documentation with actual results.

Reference: [verified source contract](sources/mj5m-pzi6/README.md).
