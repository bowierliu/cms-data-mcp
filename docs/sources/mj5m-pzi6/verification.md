# Source-contract verification

Date: 2026-10-02. This verifies research evidence and the static source contract,
not an implemented CMS client, MCP server, or underlying clinical dataset.

## Live observations

Seven captured requests returned HTTP 200 from the fixed official HTTPS host,
without redirects or credentials. The exact bodies and receipts are in the
[evidence index](evidence/2026-10-02/README.md). The three query observations were:

- California plus exact primary cardiology specialty: count 5,634, no result rows.
- Impossible state plus the same specialty: count 0, no result rows.
- California plus impossible specialty: count 0, no result rows.

The primary count response also contained 31 schema field definitions. Query
and schema resource UUIDs agree with the metadata's first distribution. The
metadata body stayed byte-identical between 20:36:49 and 20:47:03 UTC. The primary
count completed at 20:46:14 UTC. Those facts do not prove immutable data contents
throughout the window or establish a distinct-person count.

## Offline checks performed

A Python standard-library verification against every saved receipt confirmed:

1. Exactly seven body/receipt pairs, valid JSON, correct byte lengths, and
   matching local SHA-256 values.
2. HTTP 200, zero redirects, exact HTTPS host and resolved URL, and UTC start/end
   times in chronological order for each observation.
3. All three POSTs requested `results=false, count=true`. Responses contained no
   individual rows, had nonnegative integer counts, and echoed every requested
   parameter exactly. The only extra query key was the documented resource.
4. The positive result and both negative controls match the static contract.
5. The fixed request file matches the successful receipt. Distribution ID,
   download URL, and reported release match saved authoritative metadata.
6. All 31 observed field definitions have datastore type `text`; county is absent.
   The official OpenAPI describes the count-only booleans and selected endpoint.

All checks passed. No runtime product assertions were substituted for them.
`python3.11 scripts/verify_scaffold.py` also passed after adding the documentation,
checking required files, Python syntax, local links, and synthetic eval consistency.

## Independent review

A read-only reviewer checked the contract against saved API evidence and found
no material findings. It confirmed the exact-primary-specialty restriction,
record-count semantics, nullable immutable release identity, no-row responses,
and limited scope. The parent separately recalculated all hashes and read the
current CMS dictionary for field meanings and the 12-month lookback. The reviewer
did not repeat network calls or independently reread that dictionary.

## Not established

No clinician identities, distinct-clinician counts, county mapping, row-level
quality, raw-file checksum, immutable historical snapshot, default/max page size,
rate limit, general aggregate privacy guarantee, or deployed application behavior
was established. No production Python file or dependency was changed in this task.
