# Local MCP client setup

From the `cms-data-mcp` root:

```bash
uv sync --locked --group dev
uv run python scripts/check_mcp.py
```

The check launches the actual stdio server and completes the entire synthetic
workflow through nine advertised tools, ending in CSV and verified lineage.
Add `--cache-dir data/cache/demo` to retain the artifacts. Add `--live` to exercise
only the approved public CMS aggregate.

## Cursor

This workspace already has `.cursor/mcp.json`. The portable tracked example is
[.cursor/mcp.example.json](../.cursor/mcp.example.json). For a fresh checkout,
copy it to `.cursor/mcp.json` after creating `.venv`, then open this repository
folder in Cursor. The enclosing vault is not the project root.

The configuration uses `${workspaceFolder}/.venv/bin/python` with `-I -m
cms_mcp.server`, a cache under `${workspaceFolder}/data/cache/mcp`, `--enable-live`,
and optional safe call logging. Remove `--enable-live` for offline-only operation.
No API key or global client configuration is needed.

Cursor documents project-local `mcp.json`, stdio configuration, and workspace
interpolation in its [official MCP guide](https://cursor.com/docs/mcp). Enable the
server in Customize if necessary; tool calls follow the client's approval policy.
The installed Cursor version previously observed was 3.23.12. User-run acceptance
subsequently exercised all nine tools and the synthetic happy path in real Cursor
Agent chat. It found that error payloads violated success-only output schemas.
Every schema now accepts its success envelope or the shared typed error envelope.
Restart/reconnect the MCP server so Cursor refreshes the process and schemas,
then follow the [error retest checklist](../docs/cursor-acceptance.md). Full Cursor
acceptance remains pending; the computer-control service prevented an automated
post-fix UI retest.

The exact configured command, with workspace interpolation resolved, was tested
using the official SDK client from `/tmp`: nine tools, successful fictional count,
and protocol 2026-07-28. That validates the executable configuration independently
of the current working directory, not every desktop client's UI.

## Other local stdio clients

Use the following launch shape in your client's own configuration format:

```json
{
  "command": "/absolute/path/cms-data-mcp/.venv/bin/python",
  "args": [
    "-I", "-m", "cms_mcp.server",
    "--cache-dir", "/absolute/path/cms-data-mcp/data/cache/mcp"
  ]
}
```

Append `--enable-live` only to enable the fixed public CMS endpoints. The server
waits for an MCP client on standard input; launching it alone does not print a
demo result. Stop a manually launched process with Control-C.

Start by asking the agent to run the synthetic workflow. Every saved operation
returns a `provenance_id`; use that value as `get_provenance.artifact_id`. See
[tool contracts](../docs/mcp-tools.md) for strict inputs, errors and limits.
