---
name: mcp-tool-design
description: Use when defining or reviewing cms-data-mcp tool boundaries, names, input schemas, structured outputs, or error recovery.
---

# MCP tool design

Read `docs/mcp-tools.md` and the official SDK documentation for the installed
version. Begin with a user intent and the minimum calls needed to satisfy it.
Keep domain operations independent of the MCP transport.

For each proposed tool, specify its purpose, when to use it, typed inputs with
bounds, bounded output, provenance reference, failure cases, and one realistic
example. Use registered dataset/release/artifact IDs, field allowlists, enums,
and structured filters. Clarify omitted versus null values and defaults.

Return a summary, result, scope/completeness, warnings, and a provenance ID.
Oversized results need explicit truncation or bounded pagination; never present
a truncated response as complete. Tool errors should identify the invalid input,
explain available alternatives, and provide a stable code. Distinguish protocol
errors from domain/tool errors according to the installed SDK.

Example: replace `run_query(sql, download_url, output_path)` with
`query_dataset(artifact_id, filters, select, limit)` and
`export_result(result_id, format)`. The server validates columns and operations,
owns network and output locations, and enforces resource caps. `get_schema`
accepts a field subset before another schema-search tool is justified.

Assess overlap before adding tools. Resolve latest-release metadata in one place.
Use an export tool because export changes local state and has distinct limits.
Annotations must match side effects but are not access controls. In stdio mode,
logs go to stderr. Test whether an agent can select the tool from its description;
do not equate a JSON-shaped response with a conforming MCP response.
