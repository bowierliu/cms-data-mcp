# Fixed live CMS source adapter

`CMSClient` acquires evidence for the one approved view,
`california_primary_cardiology_record_count`. Its source is CMS Provider Data
Catalog dataset `mj5m-pzi6`. The fixed count is enrollment/location records in
California whose primary specialty exactly matches
`CARDIOVASCULAR DISEASE (CARDIOLOGY)`; it does not count distinct clinicians or
include secondary-specialty matches. The documented grain and dictionary
interpretation are in the [source contract](sources/mj5m-pzi6/README.md).

The adapter is an ordinary Python component. Its synchronous `metadata()` and
`retrieve(source)` methods are intended for an application worker thread, where
they manage asynchronous HTTP internally. The application controls whether live
access is enabled; constructing the client does not make a network request.
The optional transport injection exists for offline tests, not MCP tool input.

## Authority and current source evidence

Metadata comes only from the [expanded CMS metadata endpoint](https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/mj5m-pzi6?show-reference-ids).
Validation requires the exact dataset identifier, title, public access level,
official landing page, CMS publisher name and publisher identifier, and one
selected distribution with the documented CSV filename and dictionary URL.
Changing distribution identifiers are resolved from current metadata. Internal
storage references are ignored and never followed. Missing or null catalog
release/modification dates remain unknown; present invalid dates are rejected.

The returned `SourceReference` contains the SHA-256 of the exact metadata body,
UTC check time, distribution identity, recorded download URL, catalog dates, and
`synthetic: false`. It does not invent an immutable publisher release ID.
The download and dictionary URLs are verified as metadata evidence; the adapter
never downloads either file.

Retrieval first re-fetches metadata and compares all source evidence except its
check time with the selected source. It sends the exact typed `count_request()`
JSON to the [fixed count endpoint](https://data.cms.gov/provider-data/api/1/datastore/query/mj5m-pzi6/0),
validates the count/query/resource contract, then fetches and compares metadata
again. Any metadata drift rejects the observation. The validated count becomes
a normalized observation and provenance record with the original source check
time, count retrieval time, local response hash, and normalization time.
No raw response is persisted by this adapter. Stable metadata does not prove
that the mutable datastore represents an immutable release.

## Network and error bounds

- Only the fixed metadata `GET` and fixed count `POST` are permitted. No arbitrary
  URL, network host, predicate, projection, offset, credentials, or raw-file
  request is accepted.
- TLS certificate verification is enabled; environment proxies and environment
  trust settings are disabled. DNS answers must all be public unicast addresses.
  The selected numeric address is pinned for the connection while Host and TLS
  certificate verification retain `data.cms.gov`, preventing a second unchecked
  hostname resolution. Redirect responses are rejected.
- Each complete metadata or retrieval operation has a 30-second deadline,
  including DNS, all metadata checks, requests, body streaming, and retry waits.
  Individual socket operations have a 10-second timeout.
  If DNS is cancelled, an OS resolver lookup may finish in an abandoned daemon
  worker; the caller returns on its deadline and no HTTP request follows that
  cancelled lookup. Wall-clock evidence must follow source selection → metadata
  recheck → count retrieval → metadata recheck → normalization; backward clock
  steps fail explicitly.
- Each request receives at most two attempts. Only HTTP 429/503 and transport
  timeouts qualify for a retry. The fallback delay is 0.25 seconds. A valid
  Retry-After value is honored only when its wait is at most two seconds;
  longer or malformed values fail without an early retry. Other transport or
  HTTP failures do not retry, and the count request never changes on retry.
- Successful responses must be HTTP 200 and `application/json`. Requests ask for
  identity encoding and compressed responses are rejected before consuming their
  bodies. Declared and streamed bodies are capped at 1 MiB. These client limits
  do not bound CMS server scan work or claim a general upstream rate limit.
- Public `SourceError` values are fixed codes with detached exception contexts.
  This component does not log bodies, rejected personal rows, or transport
  details. It does not change host-level logging configuration or promise to
  sanitize arbitrary debug instrumentation installed by an operator.

Possible codes are `source_scope_invalid`, `live_source_required`,
`source_metadata_invalid`, `source_changed`, `count_response_invalid`,
`source_clock_invalid`, `source_address_rejected`, `source_http_error`,
`source_response_invalid`, `source_timeout`, and `source_unavailable`.
Refresh metadata after `source_changed`; do not fall back to raw data after any
failure. The application maps these codes to user-facing recovery guidance.

## Verification and dependency evidence

Implementation uses installed HTTPX2 2.13.1 and its documented
[streaming API](https://httpx2.pydantic.dev/async/),
[environment controls](https://pydantic.dev/docs/httpx2/api/environment_variables/),
and [SNI extension](https://pydantic.dev/docs/httpx2/advanced/extensions/).
The synchronous interface uses AnyIO to manage the asynchronous operation and
its overall deadline. Declare HTTPX2 and AnyIO directly as runtime dependencies
when integrating this component rather than relying on the MCP SDK's transitive
dependencies.

The 71 offline tests in `tests/unit/test_sources.py` exercise metadata authority,
missing versus invalid dates, duplicate JSON keys, drift before/after retrieval,
strict count/query/resource checks, source scope, safe errors, redirects, retries,
body/compression limits, total deadlines, and DNS pinning/private-address refusal.
They use mocked transports and recorded non-identifying metadata/count evidence;
they do not contact CMS. Live observations and end-to-end product verification
must be recorded separately by the explicitly enabled integration workflow.
