# Offline application verification — 2026-10-04

Scope: [application operations](offline-workflow.md), a packaged synthetic fixture,
and the runnable CLI. No MCP server, live request, new dependency, analytics engine,
or export operation was introduced.

Environment: local macOS, Python 3.11.15, Pydantic 2.13.5, existing `uv.lock`.

```bash
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache pytest -q
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache ruff format --check .
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache mypy src scripts
uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache python scripts/verify_scaffold.py
uv build --offline --cache-dir /tmp/cms-data-mcp-uv-cache
```

Results: 105 tests passed (86 prior tests plus 19 workflow cases). Lint, formatting,
strict typing for seven source/script files, scaffold/link checks, and package
builds passed. The first workflow test run failed collection because `service.py`
did not yet exist.

New coverage exercises real parser/provenance/storage integration, repeatable
materialization, source revalidation, synthetic-only scope, invalid count/query/
row/time input, failure before publication, missing/corrupt/wrong-source artifacts,
safe errors, and subprocess runs for default and persistent CLI modes. The
temporary-cleanup test sets the child's TMPDIR and checks that actual location.

The rebuilt wheel was reinstalled without dependency resolution into the existing
isolated verification venv. Running `python -I -m cms_mcp.demo` from `/tmp` passed:
the packaged fixture exists, the output labels five fictional records, provenance
reports a cache hit, and storage is labeled temporary. This checks installed
package behavior with already installed dependencies, not a fresh dependency setup.

The persistent demo also ran successfully against `data/cache/offline-demo`,
creating a Git-ignored synthetic artifact for inspection. The runnable commands
and expected output are in [the example](../examples/offline_count.md).

Independent review found no blocking or material correctness issues. Its cleanup
test improvement was implemented; the complete suite passed afterward. The reviewer
also identified an old distribution wheel, which was rebuilt before acceptance.

Still outside this evidence: MCP clients/stdio, live CMS access, generalized
query/export, agent evals, non-POSIX storage, and upstream dataset quality.
