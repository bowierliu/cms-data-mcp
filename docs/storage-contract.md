# Immutable local count artifacts

This implements the next unit of Phase 2: local storage for the approved fixed
count and its existing provenance. No live client or MCP server is included.

`LocalArtifactStore(root)` takes a trusted application configuration path.
`put(provenance) -> str` accepts validated, unserved provenance and returns
`artifact:<sha256>`. `get(artifact_id, *, expected_source_ref, served_at)` verifies
the file and exact source identity, then returns a new provenance value marked
as a cache hit. Retrieval/check/normalization times and stored bytes stay intact.

A single canonical JSON document contains `format_version: 1` and `provenance`.
It includes the normalized count, source evidence, fixed scope, and lineage.
The artifact ID hashes these exact bytes; the filename is `<sha256>.json`.
One file avoids partial multi-file manifest publication. Only the normalized
allowed fields are persisted. Raw responses, query payloads, and clinician rows
are not accepted. The cap is 64 KiB per artifact. Unknown formats, malformed or
noncanonical JSON, model violations, and hash mismatches are rejected.

Publication writes a private temporary file in the same directory, flushes and
fsyncs it, then creates the final name with an exclusive hard link. Concurrent
identical writes are idempotent; an existing different/corrupted file is never
replaced. The directory is fsynced before reporting success. Failure before
publication leaves no final file; a failure after publication may leave a complete
file and can be retried. Normal error paths remove temporary files. Process death
may leave an ignored `.pending-*` file; no cleanup scheduler is added here.

Supported storage is a trusted local POSIX filesystem (macOS/Linux primitives).
The root and artifact file cannot be symlinks. Operations use a directory file
descriptor, validated identifiers, and regular-file bounded reads. The root's
parent directories must be controlled by the application; defending against a
hostile process with access to those parents is outside this boundary. No
network-filesystem, Windows, power-loss, or adversarial-writer guarantee is claimed.
See Python's [filesystem APIs](https://docs.python.org/3.11/library/os.html#files-and-directories).

Cache identity is exact: metadata hash/check time, distribution, synthetic flag,
fixed predicates, response hash, retrieval time, and normalization lineage all
contribute. No latest lookup, freshness policy, or arbitrary filter interface is
introduced. Local hashes detect accidental changes; they do not prove authorship.
Raw response integrity cannot be rechecked because raw bodies are not stored.

Errors expose fixed codes only. Callers must not capture traceback locals or log
untrusted file contents/Pydantic details. The store does not repair corrupted
files automatically or interpret corruption as a cache miss.
