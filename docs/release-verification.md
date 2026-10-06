# First-release verification

Date: 2026-10-04. Scope: the approved fixed aggregate MVP, locally implemented
and exercised. Future datasets, county analysis, broader analytics and production
hosting are outside this release.

## 2026-10-05 error-contract follow-up

User-run Cursor acceptance confirmed the nine-tool happy path but found that
structured error payloads did not satisfy the advertised success-only schemas.
An authorized fix adds a typed error envelope to each schema through `anyOf`,
preserving the object root, strict branches, existing success data and `isError`.
The regression reproduces the missing success fields/forbidden `error` property
before the fix and validates actual error responses against advertised schemas
after it. Malformed envelopes remain rejected; an actual stdio error is checked.

The full suite now passes **296 tests**; Ruff lint/format and strict mypy pass.
Scaffold/link checks, the complete synthetic stdio demo and source/wheel builds
also pass. Independent review found no material issues and reproduced 40 focused
MCP test passes, including the error schema regressions.
Post-fix real Cursor chat testing remains pending because the computer-control
service failed to start. The original October 4 evidence below is retained as
history. See [current Cursor acceptance and retest](cursor-acceptance.md).

## Deterministic verification

```bash
uv sync --locked --group dev
uv run pytest -m 'not live'
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv run python scripts/verify_scaffold.py
uv run python scripts/check_mcp.py
uv build
```

The offline suite passes **286 tests**, covering model contracts, local storage,
parent verification, finite queries/CSV, mocked HTTP, real SDK sessions and stdio
processes. Ordinary test connections are denied; source tests inject controlled
transports/resolvers. The stdio integration test child also installs a network
audit hook. No live pytest suite is implicitly collected.

Independent review reproduced and helped resolve four important issues:

- Arbitrary string filters could enter saved requests. Finite categorical values
  and persisted-result revalidation now reject them before publication.
- Live/derived timestamps could run backward. Acquisition and serving chronology
  are now enforced with regressions for each boundary.
- An asynchronous DNS timeout could wait for resolver executor shutdown. An
  abandoned worker wait now returns on deadline; a real socket-resolver stall
  regression distinguishes the fix from a mocked async timeout.
- Limited catalog results could falsely claim completeness. `total_matches` and
  truthful `scope.truncated` now describe the returned candidates.

All four fixes were independently re-reviewed; the reviewer ran all 286 tests
and reported no remaining material findings in reviewed paths. DNS work may
finish in a background worker after caller cancellation, without subsequent HTTP.
A cancelled atomic file write may finish; no partial artifact is served.

The setup verifier checks files, links and fixture/spec consistency, not product
correctness. GitHub Actions configuration is included for the offline checks;
it has not run remotely because there is no published repository. Action versions
were checked against [checkout](https://github.com/actions/checkout) and
[setup-uv](https://github.com/astral-sh/setup-uv) official usage guidance.

## SDK, installed package and client configuration

Exercised runtime: Python 3.11.15 on macOS ARM64; MCP 2.3.0; protocol 2026-07-28;
Pydantic 2.13.5; HTTPX2 2.13.1. Exact dependency resolution is in `uv.lock`.

A source distribution and wheel were built successfully. The wheel and its
dependencies were installed in a separate temporary Python environment. That
interpreter ran `scripts/check_mcp.py` with Python `-I` from `/tmp`, passing all
nine tools and the full synthetic query/export/provenance path. This verifies
installed imports and the packaged fixture independently of the source cwd.
Fresh evaluation preparation and a recorded real MCP call also passed from
`/tmp`. Final independent checks passed Ruff lint/format, strict mypy (18 files),
scaffold/link validation and all 286 offline tests. CI YAML parsed locally.

The local `.cursor/mcp.json` uses the project's virtual environment with workspace
interpolation, an operator-owned cache, and the approved live flag. Its exact
resolved command was run from `/tmp` by the real SDK client: nine tools,
synthetic count 5, protocol 2026-07-28. Cursor 3.23.12 was found. GUI acceptance
could not be verified because the computer-control service failed to start; no
claim is made about visible discovery, `/teacher` routing or approval dialogs.

## Explicit live run

Command:

```bash
uv run python scripts/check_mcp.py --live --cache-dir data/cache/live-demo
```

Observed successful result:

| Field | Value |
| --- | --- |
| Retrieved at | 2026-10-04T19:21:40.952078Z |
| Dataset | CMS Provider Data Catalog mj5m-pzi6 |
| View | California + exact primary cardiology specialty, count only |
| Count | 5,634 enrollment/location records; not distinct people |
| Catalog released | 2026-09-10 |
| Immutable publisher release ID | null; binding unverified |
| Validation | Required fixed-count checks pass; raw quality/publisher integrity unchecked |
| Query | One row: CA / 5634 |
| Export | CSV with exactly that header/row, plus immutable manifest |
| Derived lineage | Validation → query → export; original normalization retained |

Artifact ID: `artifact:0250118a51e0f75dde28f28af55aecf52cf2845d52d2a0ba993dd088a57576f4`.
Export manifest ID: `export:f38ee152e465221c7ace6c63a0065c719a88fc8477cd4005e8f2bf1ce8ab17c4`.

The adapter fetched only fixed official metadata/count endpoints, rejected
redirects, enforced byte/time bounds, and checked metadata around the query. No
clinician rows, names, NPIs, addresses, archive or raw CSV were downloaded. Runtime
artifacts remain under the ignored cache. This single live run is compatibility
evidence at that time, not an ongoing uptime or freshness guarantee.

## Agent evaluation and remaining limits

The supervised fresh-agent run had eight correct final outcomes with one
field-name recovery, across 11 real MCP calls. See [the complete report](agent-evaluation.md)
for prompts, trace method, latency boundaries and unavailable model/token metadata.
It does not establish general agent reliability or native Cursor acceptance.

Windows/network filesystems, hostile local writers, power-loss durability,
large-table performance, general CMS discovery, arbitrary analytics, county
mapping, distinct-person counts and production deployment are not certified.
GitHub publication and license/visibility decisions remain separate user actions.
