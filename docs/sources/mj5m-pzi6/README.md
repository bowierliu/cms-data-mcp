# Source contract: CMS Doctors and Clinicians

Version 1.0.0, investigated 2026-10-02. **Decision: retain `mj5m-pzi6` for a
fixed, count-only live workflow.** Feasibility is verified; no source adapter or
MCP implementation was added.

The observed API returned **5,634 matching enrollment/location records** for
California with primary specialty `CARDIOVASCULAR DISEASE (CARDIOLOGY)`, and no
individual rows. This is not a count of distinct people or every cardiology
specialty. Evidence: [response](evidence/2026-10-02/cardiology-count.json) and
[request/receipt](evidence/2026-10-02/cardiology-count.receipt.json), completed
2026-10-02T20:46:14.207452+00:00.

The [machine-readable contract](contract.json) defines the investigated scope.
[count-request.json](count-request.json) is the exact successful request body,
not an installed tool. Evidence is public metadata, schema definitions, and
scalar counts. No clinician records or raw CSV files were downloaded.

## Authority and dataset identity

| Evidence | Value |
| --- | --- |
| Publisher | Centers for Medicare & Medicaid Services (CMS) |
| Catalog identity | `mj5m-pzi6`, National Downloadable File |
| Catalog family | Provider Data Catalog, Doctors and clinicians |
| Landing page | [Official CMS dataset](https://data.cms.gov/provider-data/dataset/mj5m-pzi6) |
| Metadata | [Official metastore endpoint](https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/mj5m-pzi6) |
| API contract | [CMS OpenAPI](https://data.cms.gov/provider-data/api/1), OpenAPI 3.0.2, API v1 |
| Query | `POST https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0` |
| Distribution | Array index `0`, observed UUID `288f7073-7fc6-5f3b-aa25-44902d5d1f8f` |
| Documentation | [CMS data dictionary](https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/physician/DOC_Data_Dictionary.pdf), pages 1 and 3–5 |

All probes used the exact HTTPS host `data.cms.gov`, without credentials, and
rejected redirects. The expanded metadata's distribution UUID matches both the
query's resource ID and returned schema ID. The `/0` path selects the first
distribution; it is not a row offset. Do not confuse this DKAN endpoint with
the separate `data.cms.gov/data-api/v1` API or import its pagination assumptions.

The catalog's public `downloadURL` was recorded but not requested. Expanded
reference metadata also exposes internal storage and local URL representations;
they are evidence only and must not be followed or added to an allowlist. The
observed storage version `1787091341` is an opaque upstream value, not a certified
publication timestamp or an immutable publisher release ID. The publisher
checksum fields are null; a hexadecimal path segment is not checksum evidence.

## Release semantics

| Field | Observed value | Interpretation |
| --- | --- | --- |
| `issued` | 2023-08-17 | Initial catalog issuance, not the current release |
| `modified` | 2026-08-18 | Reported dataset modification date |
| `released` | 2026-09-10 | Current catalog's reported release date |
| `nextUpdateDate` | 2026-10-15 | Expected future update, not available-release evidence |
| `%modified` | 2026-09-10T01:00:56-0400 | Catalog record timestamp from expanded metadata |
| Immutable release ID | Not established | Do not fabricate one from the above dates |
| Exact coverage interval / cadence | Not supplied in the observed metadata | Preserve unknowns |

This resolves the scaffold's August/September discrepancy at the **catalog**
level: August is modification, September is the reported release. Metadata fetched
before and after the probes was byte-identical. Nevertheless, the datastore is a
live endpoint: those facts do not prove the count is frozen to September's exact
file bytes. No archive was downloaded or inspected for historical membership.

Record source selection in `source_ref`, preserving catalog evidence and
observation time. Mint a local snapshot identity only from retrieved aggregate
bytes, request scope, and retrieval time. Set publisher immutable release ID to
null. HTTP Last-Modified/ETag values in receipts describe endpoint responses;
do not substitute them for dataset release or coverage dates.

The dictionary describes a 12-month claims lookback for this file. It does not
supply the exact start/end dates for this observation. Do not use the dictionary's
other files' CY 2024 labels as this dataset's coverage period.

## Verified schema and meaning

The successful count request returned **31 field definitions**, all with datastore
type `text`. These are schema metadata, not personal values. Logical field meaning
comes from the dictionary, not the database storage type.

| Purpose | API field | Scope |
| --- | --- | --- |
| State filter | `state` | Group/individual practice state; fixed value `CA` tested |
| Primary specialty filter | `pri_spec` | Primary specialty reported in the selected enrollment; one exact value tested |
| Secondary specialties | `sec_spec_1`–`sec_spec_4`, `sec_spec_all` | Present in schema, excluded from this count |
| City | `citytown` | Metadata only; no city-level live query approved by this contract |
| ZIP | `zip_code` | Metadata only; no inference of county membership |
| County | Absent | County queries remain unsupported |

One raw row is a clinician/enrollment/group/address combination. Repeated NPIs
can be legitimate. This investigation never requested NPI values and cannot
deduplicate clinicians. The exact primary-specialty label matched records; no
complete specialty vocabulary, subspecialty union, or equivalence to a taxonomy
code was established.

## The permitted aggregate

The fixed view is `california_primary_cardiology_record_count`. It uses two
equality conditions, `results: false`, `count: true`, `limit: 1`, `offset: 0`,
and a projection restricted to `state` and `pri_spec`. The server returned
`count`, `schema`, and `query`; there was no `results` field.

CMS's OpenAPI specifies that `count` ignores limit/offset and that disabling
results returns only the matching count. Therefore 5,634 is the server-reported
total for these predicates at that observation, not a one-row sample. This is
API-response validation, not validation of all underlying records or proof of
the upstream dataset's clinical accuracy.

Normalize to one analytical row:

```json
{
  "state": "CA",
  "primary_specialty": "CARDIOVASCULAR DISEASE (CARDIOLOGY)",
  "record_count": 5634
}
```

The first two values come from the validated request, not a returned clinician
row. The third comes from `response.count`. Record this transformation and its
parent response hash. There is no city column in this live aggregate; city-based
examples in the scaffold remain synthetic.

Only this broad fixed count and impossible-value controls were investigated.
Do not generalize the finding to arbitrary filters, small cells, grouped
city/ZIP results, targeted differencing queries, or person-level exports.
Removing names alone would not establish privacy safety. A future expansion
needs a concrete scope and privacy assessment; this is not a legal certification.

## Probe evidence and checks

| Probe | Expected | Observed |
| --- | --- | --- |
| California + exact primary cardiology specialty | Count-only response, nonnegative count, schema and query echo | HTTP 200; count 5,634; 31 field definitions; no result rows |
| Impossible state + valid specialty | Count zero, no result rows | HTTP 200; count 0 |
| California + impossible specialty | Count zero, no result rows | HTTP 200; count 0 |
| Metadata before / after | Same registered distribution and catalog facts | Identical body hashes |
| Expanded distribution reference | Query resource matches selected distribution | UUID matches query and schema |

Each [evidence receipt](evidence/2026-10-02/cardiology-count.receipt.json)
format records method, URL, request body, UTC start/end time, status, selected
response headers, byte count, local SHA-256, and limits. See the
[evidence index](evidence/2026-10-02/README.md) for actual files. Local hashes
identify observed response bytes; they do not replace publisher verification.

The probe used a 30-second socket timeout, a 1 MiB body cap, and no automatic
retries. A socket timeout is not a total request deadline, and a response limit
does not bound server scan work. Receipts retain the complete HTTP request needed
to reproduce each observation explicitly. The capture ran as a temporary research
script; no production client or automatically collected live test was introduced.

## Limits and error behavior for later implementation

- `limit` has documented minimum 1; the deployed maximum/default row cap and
  rate limit were not measured. No row pagination was used. Do not assume the
  500/5,000 limits of generic DKAN or another CMS API apply here.
- Validate HTTP status/content type, integer count (excluding booleans), echoed
  predicates, distribution identity, and absence of individual result rows.
  Reject unexpected rows without persisting or logging their body.
- A 400 query error or 404 source error must not trigger a fallback to raw data.
  The OpenAPI documents 503 and Retry-After under load. A future bounded retry
  may preserve the fixed request; never remove privacy restrictions to bypass
  load shedding. No error-injection or rate-limit stress test was performed.
- Keep no credentials in provenance. Source allowlists, total deadlines, response
  validation, and cache identity require real implementation and tests later.

## Next development task

Implement the typed source-reference, count-observation, and provenance models
with offline tests using this contract. Test unknown publisher release identity,
wrong predicate/resource echoes, forbidden rows, invalid count types, and preserved
retrieval times. Do not begin live ingestion or add the full MCP surface yet.
