---
name: data-validation
description: Use when checking CMS or synthetic artifact schemas, types, nulls, duplicates, row counts, checksums, completeness, or schema drift.
---

# Deterministic data validation

Validate an immutable artifact against a versioned contract and its declared
scope. Read `docs/provenance.md` and preserve source values before normalization.

Return a report containing artifact/hash, contract version, scope, check ID,
severity, observed value, expected condition, status, and explanation. Individual
checks use `pass`, `fail`, `warning`, or `not_checked`. An overall result never
hides failed required checks behind successful optional checks.

| Check | Interpretation |
| --- | --- |
| Byte integrity | Compare calculated digest to a recorded digest; identify its origin |
| Schema | Required fields/types, unknown fields, and version-aware drift |
| Nulls/ranges | Use documented semantics; suppression is not a zero |
| Duplicates | Check documented row keys, not convenient single identifiers |
| Row counts | Compare equivalent releases and filter/pagination scopes |
| Completeness | Record limits, pages, truncation, and unresolved totals |

Example: a 50-row limited extract can pass its type checks and remain incomplete
against a much larger catalog. Repeated NPIs do not fail uniqueness when rows
represent enrollment/location records. A new column is drift to assess; a missing
required column blocks dependent queries. Reject corrupted artifacts without
rewriting evidence to make them appear valid.

A matching local hash does not verify CMS authorship. A missing publisher digest
is `not_checked` for publisher-integrity comparison, not a fabricated pass or an
automatic failure of every quality check. Keep source authority, transport
integrity, schema compatibility, and data quality as separate findings.

Use synthetic examples for errors; never log personal rows. Do not claim dataset
correctness or clinical suitability beyond the checks actually performed.
