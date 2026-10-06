# First local MCP adapter

Historical design for the first two-tool milestone. The completed nine-tool
surface and current provenance lookup contract are in [mcp-tools.md](mcp-tools.md).
See [release verification](release-verification.md) for the current checkpoint.

Scope: expose the existing fixed synthetic workflow over stdio. Use official
`mcp` 2.3.0, locked in `uv.lock`, with its low-level typed request handlers.
The SDK owns protocol negotiation and transport. Explicit Pydantic argument
models let this small adapter reject extra inputs and sanitize errors without
echoing rejected payloads. No custom JSON-RPC implementation is needed.

| Tool | Inputs | Result / side effect |
| --- | --- | --- |
| `materialize_synthetic_count` | Empty object; no additional fields | Validates and persists the packaged fixture; returns count, artifact/source/snapshot IDs, scope, warnings, and original provenance ID |
| `get_provenance` | Required `artifact_id`, exactly `artifact:` plus 64 lowercase hex digits; no additional fields | Verifies the exact packaged source and artifact; returns provenance with a fresh serving time and no writes |

Both return structured JSON and equivalent text content. Successful envelopes
contain `summary`, `data`, `scope`, `warnings`, and `provenance_id`. The scope
labels the data synthetic, the fixed CA/primary-specialty predicate, record grain,
and completeness only for that fictional view. A provenance ID hashes the returned
record; lookups use the persistent `artifact_id`, not a provenance-ID index.

Arguments are strict and bounded. Domain/input failures are MCP tool results with
`is_error=true` and a stable JSON error code, safe explanation, and recovery step.
Unknown tool names are protocol invalid-parameter errors. Adapter-generated tool
errors and unknown-tool errors do not echo caller values, local paths, or exception
details. This guarantee does not cover SDK-level protocol errors or debug logs;
for example, an unknown JSON-RPC method may be reflected in error data.
Success JSON is capped at 16 KiB (the SDK
result includes both structured and text copies); oversized output fails explicitly.
Existing 64 KiB stored-artifact limits remain. This is not a generic protocol frame
size limit or proof of upstream dataset correctness.

Creation is annotated non-destructive, idempotent, and writing local state.
Provenance reads are annotated read-only; their serving timestamp means returned
bytes can change between reads. Both tools are closed-world. Annotations describe
behavior; validation enforces it.

Lookup compares both the observation and normalization lineage against the
packaged fixture before returning its label. A matching source reference alone
is insufficient: a different count, retrieval time, or normalization time is
rejected with `SOURCE_SCOPE_MISMATCH`. Serving time may change independently.

`python -m cms_mcp.server --cache-dir <trusted-local-directory>` runs stdio only.
The required directory is operator startup configuration, never a tool parameter.
Stdout is reserved for protocol messages. The packaged fixture loader moves from
`demo.py` to `synthetic.py`, shared by the CLI and server; its data and identity
stay unchanged. The server does not install itself into an editor or alter client
configuration.

## Execution and acceptance

1. Verify official SDK docs and installed signatures; lock the dependency.
2. Write real SDK discovery/schema/call/error tests before adapter code. Use a
   controlled clock and reject network connections in tests.
3. Implement two handlers and a stdio entry point, preserving the existing demo.
4. Exercise a subprocess with the SDK client: handshake, discovery, creation,
   provenance lookup, invalid calls, clean shutdown, and persistence across restarts.
5. Review, run all tests/lint/type/build checks, and test the installed wheel.
   Document client startup and update the checkpoint with the exercised matrix.

References: [official SDK](https://github.com/modelcontextprotocol/python-sdk),
[low-level server](https://py.sdk.modelcontextprotocol.io/advanced/low-level-server/),
[client testing](https://py.sdk.modelcontextprotocol.io/get-started/testing/).
