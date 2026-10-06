# cms-data-mcp scaffold verification

Date: 2026-10-01. Scope: Phase 0 setup, not runtime CMS/MCP functionality.

## Checks

The environment resolved with Python 3.11.15; `uv.lock` records 14 packages,
including this project. Runtime dependencies remain empty. The dependency
download initially encountered sandbox DNS restrictions, then succeeded with
authorized network access. Subsequent checks ran offline.

| Check | Command / method | Outcome |
| --- | --- | --- |
| Scaffold | `python3.11 scripts/verify_scaffold.py` | Pass: required files, TOML, Python syntax, relative links, fixture/eval consistency |
| Lint | `uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff check .` | Pass |
| Format | `uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff format --check .` | Pass |
| Types | `uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache mypy src scripts` | Pass: 3 Python files |
| Canonical skills | Skill creator's `quick_validate.py` on each of 7 `skills/*` directories | All 7 pass |
| Cursor metadata | Parse YAML for 7 agents, 12 domain/command adapters, and `.mdc` rule | Pass: required metadata, matching names, inherited models, always-applied rule |
| Packaging | `uv build --offline --cache-dir /tmp/cms-data-mcp-uv-cache` | Source distribution and wheel build |
| Wheel installation | Install wheel offline into a fresh temporary environment; import with `python -I` outside the project | Pass: distribution version 0.0.1, import from site-packages, `py.typed` included |
| Git boundary | `git rev-parse --show-toplevel`, branch and remote inspection | Inner `cms-data-mcp` is the root; `main`; no remote |
| Git exclusions | Check secret/runtime paths and list unignored source files | Runtime paths excluded; `.env.example`, synthetic fixture, cache policy, and lockfile retained |
| Product test collection | `uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache pytest --collect-only -q` | Exit 5, no tests collected; expected absence, not a passing suite |

The lint/format/type passes followed correction of one long output line and a
reused variable's inconsistent type in the setup script. An initial ignore-check
assertion was corrected to account for this Git version reporting matched
negation patterns; `git ls-files --others --exclude-standard` confirmed the
intended tracked candidates. No ignore policy change was needed.

The scripts perform setup checks only. Package build/install does not establish
an operational CMS pipeline, supported client matrix, or usable server.

## Skill application review

A read-only baseline exercise evaluated seven cases before the domain skills
were written: conflicting release evidence, a deceptive redirect, NPI/location
grain and county assumptions, an unsafe query interface, partial-data validation,
overclaimed MCP tests, and corrupt cache lineage.

The baseline handled most evidence distinctions correctly. Its modeling answer
recommended distinct-NPI counting without first applying the supplied no-PII
constraint. The canonical modeling skill now starts with the privacy boundary,
uses synthetic identifiers for explanation, and separates live aggregates from
person-level ingestion. User-requested reference skills were retained even where
baseline reasoning already handled the scenario; no measured uplift is claimed.

A separate read-only agent applied all seven completed skills to the scenarios
and inspected the scaffold. It correctly preserved the privacy restriction,
source uncertainty, row grain, county limitation, bounded query/export interface,
independent validation statuses, testing scope, and append-only lineage.

The reviewer found one important design inconsistency: metadata required a
snapshot ID before retrieval could create it. The contract now separates
metadata's `source_ref`, optional publisher release ID, and retrieval's local
`snapshot_id`. A follow-up review confirmed alignment across the architecture,
tool contract, provenance, examples, and synthetic eval sequence. No material
finding remains from that review. These are instruction-application observations,
not statistical evaluations of model reliability.

## Explicitly unverified

No MCP server, CMS HTTP adapter, validation engine, DuckDB implementation, or
exporter exists. Product tests and executable agent evaluations have not run.
No live editor session has demonstrated command discovery or teacher delegation.
No exact latest CMS release or data distribution has been certified.
