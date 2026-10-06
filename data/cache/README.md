# Runtime cache boundary

Only this document is versioned. Cache contents are disposable local
artifacts and are ignored by Git. The cache is not a place to store PHI, PII,
employer data, or secrets; being ignored does not make such data acceptable.

`cms_mcp.storage.LocalArtifactStore` stores one canonical JSON file per normalized
count and its provenance, using a content hash as the filename. It publishes
atomically without overwriting files and verifies bytes/models/source identity
on read. Cache hits preserve acquisition timestamps. Raw responses and clinician
rows are never store inputs. Tests use temporary directories, not this directory.

Only trusted local POSIX filesystem storage is supported. Interrupted processes
may leave `.pending-*` files that are never read as artifacts. See the
[storage contract](../../docs/storage-contract.md) for failure and scope limits.
