# cms-data-mcp roadmap status

| Milestone | Current result |
| --- | --- |
| 0 — Scaffold | Complete: files, roles, commands, skills, rules, package and setup checks |
| 1 — Source contract | Complete: one CMS dataset, verified fixed count-only request, documented limits |
| 2 — Synthetic workflow | Complete within fixed aggregate scope: metadata, retrieval, validation, query, CSV and provenance through MCP |
| 3 — Permitted live slice | Implemented and verified end to end with the approved scalar count, source checks and immutable cache |
| 4 — Evaluation/hardening | Offline suite and reviewed failure cases complete; one supervised eight-scenario agent run recorded; wider model/client acceptance remains future work |
| 5 — Local portfolio demo | Runnable documented demo, installed-package verification and accurate resume evidence; GitHub publication is a separate user decision |

The completion boundary is [the first-release plan](completion-plan.md). It
intentionally narrows earlier city-level synthetic examples to the same one-row
aggregate used live, uses typed filtering instead of unnecessary DuckDB, and
exports CSV only. Those choices are recorded in [ADR 002](adr/002-fixed-aggregate-mvp.md).

The remaining local acceptance item is Cursor's visible tool discovery and
approval flow: configuration and executable launch work, but the UI automation
service was unavailable. Repeated model evaluations, a broader supported-client
matrix and additional operating systems are future verification work.

County support, another dataset, historical comparison, larger analytics,
Parquet and warehouse export need new source evidence and contracts. They are
not unfinished parts of this fixed-view release. [PROJECT_STATE.md](../PROJECT_STATE.md)
is the current checkpoint.
