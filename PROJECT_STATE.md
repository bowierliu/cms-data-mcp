# cms-data-mcp project state

Updated: 2026-11-21.

## Current phase

The approved single-source MVP is implemented and verified locally: discovery →
metadata → schema → aggregate retrieval → validation → constrained query → CSV
export → provenance. The broader future roadmap remains explicitly deferred.
User-run Cursor acceptance confirmed all nine tools and the synthetic happy path,
but exposed an error-output schema defect. The schema fix passes local regression
checks; full Cursor acceptance remains pending a real chat error retest.

## Recruiter access

The static replay presents a captured synthetic stdio run in a browser. The
local web companion uses an operator-controlled ledger, OpenAI and real MCP
tools over the SDK’s in-process transport. The only questions concern validation
or lineage of the packaged fictional aggregate. The original stdio server and
opt-in public CMS count remain available. [Use the demo](README.md#try-the-demo).

## Completed

- Repository scaffold, seven specialist roles, five commands, seven domain skills,
  native Cursor discovery adapters, project rules, documentation and fixtures.
- Verified CMS Provider Data Catalog `mj5m-pzi6` and its fixed count-only contract.
  No personal clinician records or raw CSV were fetched.
- Strict source/count/provenance models, immutable bounded local storage and shared
  synthetic fixture; original application-only demo remains compatible.
- Curated discovery, dictionary field explanations, opt-in live metadata/count
  adapter with bounded networking, source-drift checks and chronology enforcement.
- Explicit validation reports, finite projection/filtering over one aggregate,
  persisted query results, CSV export and complete verified parent lineage.
- Nine MCP tools, strict schemas, safe errors, output limits, optional JSON call
  logging, real SDK/stdio integration, full offline/live demo and client example.
- Local `.cursor/mcp.json` created and its command verified from a different cwd.
- Supervised fresh-agent evaluation: eight correct final outcomes with one NPI
  field-name recovery. Exact model ID/token usage not exposed by the host.
- Independent review findings fixed with regressions: arbitrary string persistence,
  clock ordering, DNS deadline behavior, and catalog truncation.
- Shared typed error envelopes now appear alongside success envelopes in every
  advertised output schema. Explicit schema tests cover errors for all nine tools,
  malformed envelopes, and an actual stdio error response.

## Architecture and decisions

One `src/cms_mcp` package. `api.py`/`server.py` → `workflow.py` → `sources.py`,
`analytics.py`, typed models and immutable file stores. `catalog.py` supplies the
curated mapping; `synthetic.py` supplies the packaged offline example.

Official project/repository/distribution name: `cms-data-mcp`. Python import:
`cms_mcp`. The enclosing vault is a container, never an input or Git remote.

Direct dependencies: Pydantic, official MCP SDK, AnyIO and HTTPX2, locked in
`uv.lock`. Direct typed filtering is sufficient for the one-row aggregate; no
DuckDB/Parquet/general analytics dependency is added. See
[ADR 002](docs/adr/002-fixed-aggregate-mvp.md).

Default server startup is offline. The configured local Cursor example enables
only the approved public CMS metadata/count endpoints. Paths are operator startup
settings, never tool parameters. Live retrieval never widens predicates or falls
back to a raw file. Full-file and personal-row retrieval remain prohibited.

Count artifacts sit at the cache root; `records/` holds source/report/result/export
JSON and `exports/` holds CSV. Cache hits preserve acquisition evidence. Derived
provenance rechecks all parents. Local hashes do not imply publisher verification.

## Verification

- 296 offline tests pass after the error-contract fix, including simulated HTTP,
  actual stdio processes and explicit validation of error output schemas.
- Ruff lint/format, strict mypy, scaffold/link checks and locked environment checks
  pass. Source distribution/wheel builds and the complete installed-wheel stdio
  workflow from `/tmp` also pass; fresh evaluation tooling was exercised there.
- Live demo on 2026-10-04T19:21:40.952078Z: 5,634 enrollment/location records,
  validation pass, saved query/CSV, three derived lineage steps, catalog release
  2026-09-10 and immutable publisher release ID null.
- SDK 2.3.0 / protocol 2026-07-28; Python 3.11.15 on macOS ARM64.
- Independent re-review found no remaining material issues in the reviewed paths.
- [Release verification](docs/release-verification.md), [agent evaluation](docs/agent-evaluation.md),
  [demo](docs/demo.md), and [resume evidence](docs/resume.md) contain details.

## External acceptance and limits

- User-reported Cursor Agent testing exercised all nine data tools successfully:
  count 5, six required checks, query CA/5, exact CSV and provenance. Unsupported
  county/distinct-person requests did not invent values. Error handling failed
  with opaque -32602 responses before the authorized schema fix.
- Post-fix Cursor error acceptance is still pending: the computer-control service
  again failed to start on 2026-10-05. Automated schema/stdio evidence does not
  substitute for that retest. See [Cursor acceptance](docs/cursor-acceptance.md).
- The GitHub repository is public. Offline CI has run successfully. The hosted
  demo is static. The local companion uses mocked provider responses in tests.
- Current query scope is one fixed aggregate row; no city/county/ZIP filtering,
  distinct-person counting, arbitrary SQL/URLs/paths, grouped data or comparisons.
- Raw data quality, publisher integrity, immutable release binding and exact
  coverage interval remain unchecked/unknown. Stable metadata is not a snapshot
  guarantee. The dictionary describes a 12-month lookback without exact dates.
- Storage has been exercised on local macOS POSIX filesystems. Windows/network
  filesystems, hostile local writers and power-loss guarantees are not certified.
  Cancelled writes may finish atomically; cancelled DNS work may finish in an
  abandoned worker. Complete unreferenced files can remain after failures.

## Next action

Restart/reconnect the Cursor MCP server to load the changed tool schemas, then
repeat the six error cases in the [acceptance checklist](docs/cursor-acceptance.md).
Keep full Cursor acceptance pending until readable domain errors are observed.

Future expansions need their own evidence and acceptance criteria: county
crosswalks, additional datasets, general analytics/DuckDB, Parquet, historical
comparison, repeated named-model evals and optional warehouse export.
