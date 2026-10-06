# Offline application workflow

This step connects the existing parser, provenance models, and immutable store.
That application slice adds no transport, live CMS access, query engine, or export
tool. The subsequent [MCP adapter](mcp-adapter.md) now exposes its fixed synthetic
workflow over local stdio.

`CountService(store)` exposes two typed Python operations:

- `materialize_count(body, *, source, retrieved_at, normalized_at)` validates
  source evidence, requires `synthetic=True`, parses the fixed count response,
  records normalization, and publishes it. It returns an immutable
  `CountArtifact` containing the artifact ID and original provenance.
- `get_provenance(artifact_id, *, expected_source_ref, served_at)` checks stored
  integrity and exact source identity, then returns synthetic provenance marked
  as a cache hit. Stored bytes and original evidence remain unchanged.

Inputs and timestamps are explicit; the service does not fetch data or invent
acquisition times. `CountServiceError` carries fixed error codes without chained
payload-bearing errors. Validation precedes publication. A storage failure is
never treated as success or repaired by silently replacing an artifact. Existing
storage limits, trusted-root requirements, and post-publication failure semantics
continue to apply. Synthetic flags are declarations by the fixture supplier,
not automatic proof that arbitrary caller-provided bytes contain no real data.

`python -m cms_mcp.demo` loads packaged `fixtures/synthetic-count-v1.json`, creates
an artifact, opens a fresh service/store, retrieves provenance, and prints JSON.
The fixture declares five fictional matching enrollment/location records, not
five people. It emulates the verified fixed-count response; it is separate from
the older city-level CSV fixture. Its timestamps and distribution identity are
fictional, and its metadata hash covers canonical synthetic metadata.

The default demo uses a temporary directory removed on exit. Use
`--cache-dir data/cache/offline-demo` to retain the artifact in a trusted local
directory. This is human/operator configuration, not an MCP input. The output
labels synthetic data and temporary/persistent storage explicitly. Repeated runs
with the same fixture retain one artifact; only serving time and the returned
served provenance ID change. No raw response is persisted. Runtime demo failures write
a fixed JSON error to stderr and exit nonzero without a success document.
Argument/help handling uses standard argparse output.

## Implementation and acceptance

1. Add end-to-end tests against real temporary files and subprocess demo execution.
2. Implement `service.py`, the packaged fixture, and `demo.py` without new runtime
   dependencies. Keep MCP adapters separate from these operations.
3. Check invalid responses/source/times publish nothing; missing/corrupt/wrong-source
   artifacts fail explicitly; repeat runs preserve acquisition evidence.
4. Independently review, run the full test/lint/type/build checks, and execute the
   demo from an installed wheel outside the repository. Update the checkpoint.

Completed 2026-10-04; see [verification](workflow-verification.md) and the
[runnable example](../examples/offline_count.md).
