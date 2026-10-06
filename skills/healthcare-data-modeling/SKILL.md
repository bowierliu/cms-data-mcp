---
name: healthcare-data-modeling
description: Use when interpreting CMS row grain, provider or facility identifiers, specialty fields, geography, dates, or join semantics.
---

# Healthcare data modeling

Build a dataset-specific mapping from documented source fields to typed concepts.
Read the source dictionary for the selected release; do not transfer assumptions
between CMS dataset families.

Check privacy before choosing a model. Under this project's no-PII constraint,
do not ingest real names, NPIs, addresses, or person-level records. Explain
identifier semantics using synthetic examples. Public availability is not an
exception. Use verified non-identifying aggregates for the planned live slice.

| Concept | Modeling decision |
| --- | --- |
| Row grain | Write what one row represents before defining uniqueness |
| NPI / provider ID | Preserve as strings; an NPI alone need not identify a row |
| Facility / plan / contract ID | Preserve formatting; identify the issuing namespace |
| Specialty / taxonomy | Keep source vocabulary; map only with cited definitions |
| Dates | Separate coverage interval, publication, modification, and retrieval |
| Geography | Distinguish practice location, mailing address, city, ZIP, and county |

For joins, document keys, expected cardinality, unmatched rows, and row-count
changes. Do not silently deduplicate or multiply records. Keep suppressed and
missing values distinct from zero; preserve raw and normalized values separately.

Example: two synthetic rows sharing an NPI but having different practice
locations may both be valid. Record count is not distinct-clinician count.
City `San Diego` is not San Diego County. County filtering needs a documented
county field or an approved, versioned geographic mapping with ambiguity handling.

Return the grain, field/type/meaning mapping, candidate keys, permitted joins,
count semantics, transformation rules, and unresolved assumptions. Add only the
healthcare concepts used by the current source.
