# Local MCP adapter verification

Historical two-tool checkpoint, superseded by the completed workflow's
[release verification](release-verification.md). Counts and claims below describe
that earlier milestone only.

Verified 2026-10-04 on local macOS ARM64 with Python 3.11.15.
This covers the two packaged synthetic tools, not the full Phase 2 roadmap.

| Component | Exercised version / boundary |
| --- | --- |
| Server package | cms-data-mcp 0.0.1 |
| Official SDK and client | mcp 2.3.0, locked in uv.lock |
| Negotiated protocol | 2026-07-28 |
| Pydantic | 2.13.5 |
| Transports | SDK in-process sessions and real local stdio subprocesses |
| Data | Packaged synthetic-count-v1, fictional count 5 |
| Desktop clients | Not acceptance-tested |

## Checks and results

Run from the project root:

```bash
uv run pytest -m 'not live' -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src scripts
uv run python scripts/verify_scaffold.py
uv run python scripts/check_mcp.py
uv build
```

All 127 tests passed: the previous 105 domain/storage/application tests plus 22
MCP/client cases. Ruff lint and formatting passed (79 files); strict mypy passed
for 10 source/script files. Scaffold/link validation passed. Source distribution
and wheel builds passed. The existing offline demo still returns the same
artifact and snapshot identities after extracting the shared fixture loader.

The MCP cases cover discovery, strict argument schemas and tool annotations,
successful output-schema validation, safe adapter errors, rejected extra fields,
malformed IDs, missing/corrupt artifacts, source mismatch, fixed-fixture evidence,
storage failure, and output-size rejection. A real stdio session creates an
artifact, handles an invalid call, shuts down, restarts, and reads the same bytes.

Tests deny outbound socket connections in-process and install a network-denial
audit hook before starting the stdio test child. No CMS request is made. This
does not certify network isolation of arbitrary future code or desktop clients.

Independent review found that source-reference equality alone could label a
different observation as the packaged fixture. Three regression cases (changed
count, retrieval time, normalization time) failed before the correction and pass
afterward. Lookup now compares the observation and normalization lineage with
the packaged evidence, without modifying storage. Re-review reported no remaining
material issues. Documentation also now limits sanitization claims to the adapter;
SDK protocol errors can include a caller's unknown method name.

## Installed package check

Built `dist/cms_data_mcp-0.0.1-py3-none-any.whl`, installed it with its dependencies
into a separate temporary Python environment, and ran `scripts/check_mcp.py` using
that interpreter with `-I` from `/tmp`. The script launched an isolated child
server from the installed package, discovered both tools, and returned:

- `server`: `cms-data-mcp`
- `sdk_version`: `2.3.0`; `protocol_version`: `2026-07-28`
- `synthetic`: `true`; `record_count`: `5`; `cache_status`: `hit`
- Original `retrieved_at`: `2026-01-01T00:00:01Z`

This proves the wheel includes the server and fixture and works outside the
source checkout. An initial offline install lacked a cached dependency wheel;
allowing dependency resolution from the registry completed the installation.
No live CMS access was involved in installation or the workflow.

## Limits

Successful JSON is capped at 16 KiB; MCP returns it as both structured data and
text. Stored artifacts remain capped at 64 KiB. These are application limits,
not a global protocol-frame limit. Filesystem work runs off the event loop; a
cancelled call can finish an atomic write, and retry is idempotent. Cancellation
timing and power-loss behavior are not separately certified here.

No live CMS adapter, general query/export, quality report, agent eval, editor
discovery acceptance, or HTTP deployment has been tested or added. Counts are
fictional records, not distinct clinicians. See [local setup](../examples/mcp_stdio.md)
and [adapter contracts](mcp-adapter.md) for the implemented surface.
