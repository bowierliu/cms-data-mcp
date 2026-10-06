# CMS source observations — 2026-10-02

These are real public CMS API responses, not synthetic fixtures. They contain
dataset/schema metadata and scalar counts, with no individual clinician values.
They support the [source contract](../../README.md), not a claim that runtime
tools are implemented. Do not copy the real count into a synthetic fixture.

Each `.json` body is saved byte-for-byte; its `.receipt.json` records the exact
method, URL, JSON request if applicable, UTC timing, HTTP status, byte length,
selected response headers, and local SHA-256 of those body bytes. An absent
HTTP validator or publisher checksum remains absent. Receipts are observation
records and were generated locally, not signed by CMS.

| Body | Receipt | Purpose |
| --- | --- | --- |
| [metadata-before.json](metadata-before.json) | [receipt](metadata-before.receipt.json) | Dataset identity, catalog dates, public distribution URL |
| [openapi.json](openapi.json) | [receipt](openapi.receipt.json) | Official query and response contract |
| [cardiology-count.json](cardiology-count.json) | [receipt](cardiology-count.receipt.json) | California/primary-cardiology count and schema, with no result rows |
| [negative-state-count.json](negative-state-count.json) | [receipt](negative-state-count.receipt.json) | Impossible-state control returns zero |
| [negative-specialty-count.json](negative-specialty-count.json) | [receipt](negative-specialty-count.receipt.json) | Impossible-specialty control returns zero |
| [metadata-references.json](metadata-references.json) | [receipt](metadata-references.receipt.json) | Resolve the distribution UUID to the query resource |
| [metadata-after.json](metadata-after.json) | [receipt](metadata-after.receipt.json) | Confirm catalog body stability across observations |

All seven captured requests returned HTTP 200 without authentication or redirects.
An earlier metadata-only connectivity probe also succeeded but is not archived
here. A sandbox DNS failure preceded the authorized direct network requests.
No raw data file, archive, internal storage path, or third-party URL was fetched.

Expanded metadata contains source-side internal URL representations. Preserve
them as observed metadata only; never treat them as approved fetch destinations.
Likewise, schema fields named `npi` or `provider_first_name` are field definitions,
not a license to request their values.

Reproduction is opt-in: use the recorded request method, URL, and JSON with a
read-only HTTP client, reject redirects, enforce a body cap, and require no result
rows before saving. Counts and schemas may change. Create a new observation
directory for a later capture rather than overwriting this evidence. A matching
future count alone would not prove identical underlying data.
