# Integration test boundary

`test_storage.py` exercises local artifact storage using synthetic provenance and
temporary directories. It covers persistence, idempotence, concurrent publication,
hash/model corruption, source scope, file-size bounds, path/symlink/special-file
rejection, safe errors, and injected failures before/after atomic publication.
These tests use local POSIX filesystem primitives; they do not access CMS.

`test_workflow.py` connects the parser, provenance, service, and real artifact
store. It verifies repeatable materialization, source/time validation before
publication, scoped lookup, preserved evidence, and failures without unsafe
payloads. Subprocess cases run the packaged CLI in isolated Python from temporary
working directories, exercising ephemeral and persistent demos.

`test_mcp_server.py` uses the official MCP SDK against the local synthetic server.
It covers discovery, strict inputs, successful output schemas, safe tool errors,
source/fixture identity, corruption, storage/output limits, and real stdio process
restart with unchanged stored bytes. The subprocess network audit hook rejects
outbound connections. A separate subprocess verifies the runnable smoke script.
See [MCP verification](../../docs/mcp-verification.md) for versions and limits.

Live CMS checks require an explicit opt-in gate before they are implemented.
Do not add network requests at test import or collection time.
