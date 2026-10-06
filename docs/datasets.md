# cms-data-mcp first dataset decision

Research date: 2026-10-02. The fixed live adapter was implemented and verified on
2026-10-04. The [source contract](sources/mj5m-pzi6/README.md) contains the exact
request, machine-readable constraints, and captured evidence.

## Selected source and permitted view

CMS Provider Data Catalog, Doctors and Clinicians **National Downloadable File**,
publisher identifier **`mj5m-pzi6`**.

- [Official dataset page](https://data.cms.gov/provider-data/dataset/mj5m-pzi6)
- [Official data dictionary](https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/physician/DOC_Data_Dictionary.pdf)
- [Official release archive](https://data.cms.gov/provider-data/archived-data/doctors-clinicians)

This source is a strong subject for the specialty/location workflow because the
dictionary describes primary and secondary specialties and practice geography.
Its rows represent clinician/enrollment/group/address combinations; one clinician
can appear more than once. It is a large national dataset, so the first slice
must not depend on downloading the entire file.

The live response verified API fields `pri_spec`, `citytown`, `state`, and
`zip_code` among 31 text field definitions. A count-only request using `state=CA`
and exact primary specialty `CARDIOVASCULAR DISEASE (CARDIOLOGY)` returned 5,634
matching records with no clinician rows. Invalid-state and invalid-specialty
controls both returned zero. Secondary specialties and other cardiology labels
are outside this view. NPI is not a row key; records are not distinct people.

## Constraints on the first slice

The user excludes PII even when it is publicly available. The source contains
personal clinician fields, so **raw person-level retrieval is out of scope**.
The repository stores synthetic analytical rows plus captured public metadata,
schemas, and scalar count evidence. The verified live view uses the documented
`results=false, count=true` path; it never requests names, NPIs, contact details,
or addresses. This finding covers the fixed broad California/primary-cardiology
count only. Small-cell, targeted differencing, or grouped/narrower requests need
their own scope assessment; removing names alone is not a privacy assessment.

If that access pattern becomes unavailable, stop this source's live-ingestion
work and report a recommendation for an institutional or already aggregated CMS
source. Do not quietly download the raw file or imply that a different dataset
still answers the clinician question.

The reviewed dictionary lists city, state, and ZIP, but no county field. The first
demo uses only the California aggregate, including its synthetic counterpart.
San Diego County requires verified county evidence or a separately approved
crosswalk with documented limitations; it is deferred. Never substitute city or
ZIP prefix matching for county membership.

## Release findings and remaining uncertainty

The live catalog reports `modified=2026-08-18`, `released=2026-09-10`, and
`nextUpdateDate=2026-10-15`. Its distribution UUID matches the live query resource
and schema. Metadata before and after the probes was byte-identical. This
reconciles the earlier date discrepancy at the catalog level.

The query remains a timestamped observation of a mutable datastore. Neither
those dates nor stable metadata prove that its rows are frozen to an immutable
September release. No archive or raw file was fetched, and the publisher
checksum is absent. Preserve catalog release evidence separately from a local
snapshot identity. The dictionary states a 12-month claims lookback; exact
coverage dates and formal update cadence remain unknown.

## Alternatives

NPPES is a useful enumeration source but would add taxonomy interpretation, size,
and personal-record concerns. Provider utilization/payment data answers a
different, period-specific question. A hospital-level dataset better avoids
person identity but does not support the requested specialty workflow. Those are
future choices, not extra adapters in this scaffold.

## Implemented workflow

Typed models, a bounded HTTP client, source-matched caching, validation, local
query, CSV export and MCP tools now implement this view. See
[live adapter](live-source.md) and [release verification](release-verification.md).
The investigation files remain historical evidence; the live demo records a new
observation without changing that evidence.
