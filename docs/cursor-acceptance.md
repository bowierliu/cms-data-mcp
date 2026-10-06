# Cursor acceptance: error-contract follow-up

Date: 2026-10-05. **Full acceptance is pending.** Happy-path behavior is confirmed
by the user's real Cursor Agent tests. The error contract is repaired and verified
locally; readable errors have not yet been confirmed in a post-fix Cursor chat.

## User-reported acceptance evidence

- All nine tools were discovered and exercised, including the synthetic shortcut.
- Synthetic count 5, six required validation checks, query CA/5, exact CSV
  `state,record_count\r\nCA,5\r\n`, and provenance passed.
- Unsupported county and distinct-clinician requests did not invent answers.
- Six failures across metadata, schema, validation, query, provenance and export
  appeared as opaque MCP error -32602 instead of the intended domain errors.

This is user-supplied real-client evidence, distinct from the agent's SDK tests.
No source files were changed during those acceptance tests. The user explicitly
authorized the focused source fix afterward.

## Defect and fix

The server returned structured objects shaped like
`{"error":{"code":"...","message":"...","recovery":"..."}}` with
`isError: true`, but advertised only the success envelope schema.
Explicit JSON Schema validation rejected the extra `error` property and required
five missing success fields. The Python SDK's normal error path skips output
schema validation, so earlier SDK error tests did not catch this incompatibility.

`ToolError` and `ErrorEnvelope` now define the shared typed error payload. Every
tool advertises `type: object` plus an `anyOf` union of its original success model
and that error model, with shared definitions at the schema root. Both branches
reject extra properties. Error codes, messages, recovery instructions, equivalent
text content and `isError: true` are preserved. Unknown tool names still produce
protocol errors rather than domain envelopes.

The regression calls actual tools and validates their structured errors against
the output schemas returned by tool discovery, including all nine tools. It also
checks that malformed success/error envelopes and mixed envelopes remain invalid.
An existing actual stdio/restart test now explicitly validates its error output.

Local result: **296 tests pass**, including the new regressions; Ruff lint/format
and strict mypy pass. These checks address the schema boundary, not Cursor's UI.
Scaffold/link checks, the complete synthetic stdio demo and source/wheel builds
also pass after the fix. The demo retains count 5, query CA/5, exact CSV and the
three derived lineage steps on SDK 2.3.0 / protocol 2026-07-28.
Independent review found no material issues, confirmed that every configured
error code validates against every advertised output schema and that success
definitions are preserved, and reran 40 focused MCP tests successfully.

## Real Cursor retest procedure

1. Restart/reconnect `cms-data-mcp` in Cursor so the running process and cached tool
   schemas are refreshed. Use a fresh Agent chat in this project.
2. Use only the project's MCP tools and synthetic data; do not edit source files,
   fetch live CMS data, or repair intentionally invalid test requests silently.
3. Call `get_dataset_metadata` for `synthetic-count-v1` and retain its valid
   `source_ref` for the schema case below.
4. Execute the six cases below as real tool calls and inspect the tool responses.
   `ZERO64` means exactly 64 literal zero characters; substitute before calling.

| Tool | Arguments | Expected code |
| --- | --- | --- |
| `get_dataset_metadata` | `dataset_id: "unknown"` | `DATASET_NOT_FOUND` |
| `get_schema` | `dataset_id: "synthetic-count-v1"`, valid `source_ref`, `fields: ["county"]` | `UNSUPPORTED_GEOGRAPHY` |
| `validate_dataset` | `artifact_id: "artifact:ZERO64"` | `ARTIFACT_NOT_FOUND` |
| `query_dataset` | `artifact_id: "artifact:ZERO64"`, `validation_id: "validation:ZERO64"`, `limit: 0` | `INVALID_ARGUMENTS` |
| `get_provenance` | `artifact_id: "artifact:ZERO64"` | `ARTIFACT_NOT_FOUND` |
| `export_result` | `result_id: "result:ZERO64"` | `ARTIFACT_NOT_FOUND` |

Each response must preserve the expected code, a readable message and recovery
guidance with `isError: true`, rather than an opaque schema-related -32602. A tool
that the agent declines to call is an unexecuted case, not a passing error test.
Finish by repeating the synthetic happy path and the synthetic shortcut, verifying
count 5, six required checks, query CA/5, the exact CSV and original provenance.
Record Cursor version, time, actual arguments and observed responses. Mark full
acceptance only after both happy-path and error cases pass in the real client.

## Current blocker

On 2026-10-05, selecting Cursor through the available computer-control tool failed
with `Sky Computer Use service startup request failed`. No post-fix UI action or
chat error retest was possible. The MCP server has not been restarted in Cursor
by this agent. This is a test-environment blocker, not evidence of client success.
