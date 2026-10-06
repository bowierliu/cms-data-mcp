---
name: mcp-testing
description: Use when verifying cms-data-mcp tools, SDK or client compatibility, structured failures, or intent-to-tool evaluation scenarios.
---

# MCP testing

Separate tool correctness from agent usability. Read `tests/README.md` and
`tests/evals/scenarios.json` for the current stage and cases.

For deterministic tests, exercise the domain operation with synthetic fixtures,
then call the tool through the real installed SDK. Verify discovery, advertised
input/output schemas, validation errors, domain errors, bounded results, and
provenance references. Exercise the advertised transport separately; an in-memory
SDK test does not prove subprocess/stdio behavior. Record SDK, protocol, and
client versions and negotiate according to that SDK, not a remembered protocol.

Include empty results, unknown IDs, unavailable releases, partial pagination,
schema drift, checksum mismatch, invalid filters, injection attempts, traversal,
timeouts, cancellation, and output/resource caps where implemented. Offline tests
must use controlled clocks, temporary storage, and denied external network.
Live tests require an implemented opt-in gate before collection can make requests.

An agent eval records user intent, allowed tool sequences, expected parameters,
result assertions, critical failures, model/client configuration, and observed
trace. Score semantic correctness and provenance separately from call count and
token use; efficient wrong answers still fail. Fixtures must not fabricate real
CMS credentials, releases, or clinical claims.

Example: three Python unit tests do not establish that a server starts, advertises
the right tools, works with every client, or supports clinical decisions. Report
only the exercised matrix. During Phase 0, scaffold verification and eval
specifications are available; there is no product test suite or agent score.

Return commands, exit statuses, expected/observed results, failed checks, and
untested scope. Do not fix production code during a verification-only assignment.
