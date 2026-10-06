# cms-data-mcp test strategy

Unit tests now exercise typed source references, fixed count parsing, and
provenance. Integration tests exercise immutable artifact storage on real local
files, the application/CLI workflow, and actual MCP SDK sessions and stdio processes.
Supervised agent evaluation is recorded separately from deterministic tests;
see [the evaluation report](../docs/agent-evaluation.md). No live pytest suite exists.
`scripts/verify_scaffold.py` verifies setup only.

| Layer | Evidence it will provide | Boundary |
| --- | --- | --- |
| Unit | Typed contracts, release resolution, query validation, lineage | Offline, deterministic |
| Integration | Real SDK calls, immutable cache, verified parent lineage, CSV export | Temporary paths, no external network |
| Live | Authoritative metadata and permitted aggregate compatibility | Explicit opt-in, bounded requests |
| Evals | Correct tool/parameter choices for representative intents | Separate agent scorecard |

Source transport and analytical model tests use controlled HTTP responses and
the fixed one-row view. DuckDB is deferred and is not part of the test suite.

`uv run pytest -m 'not live'` is the default. There are no live tests. A `live`
marker alone does not block network access: implement an opt-in collection gate
and network denial fixture before introducing live tests. Never collect a live
test without that gate. Time, source payloads, and filesystem roots must be
controlled in ordinary tests. Record exact commands and versions in checkpoints.
Ordinary tests deny outbound connections in-process. MCP tests also install a network
audit hook in the stdio test child before server startup. This verifies the
offline adapter; it is not a sandbox guarantee for all future project code.

`src/cms_mcp/fixtures/` contains the packaged synthetic count used by the runnable
demo and workflow tests. `tests/fixtures/` stores synthetic upstream payloads. `data/fixtures/` stores
synthetic analytical rows. Do not duplicate fixtures between the two locations.
Failure coverage must include source spoofing, redirects, malformed schema,
release ambiguity, partial pagination, corrupted cache bytes, unsupported county
filters, query injection, path traversal, resource caps, and empty results.
