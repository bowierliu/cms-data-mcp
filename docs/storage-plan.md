# Local artifact storage implementation plan

Goal: persist and recover a validated count plus provenance without changing
its evidence, overwriting artifacts, or accepting out-of-scope cache data.
Spec: [storage contract](storage-contract.md).

Execution: implement inline, then request one independent review. This is the
already authorized next development task. Keep the existing uncommitted project
in place; the independent repository has no initial commit or worktree base.
No new dependencies, network retrieval, database, or MCP surface.

## Task 1 — Storage and filesystem tests

Create `src/cms_mcp/storage.py` and `tests/integration/test_storage.py`.
Inputs are the existing immutable `Provenance` models; outputs are content IDs
and validated provenance with cache serving metadata. Use temporary directories.

- [x] Write round-trip, idempotence, corruption, scope, safe error, size/path,
  concurrent-writer, and atomic-failure tests. Run them before implementation.
  The first round-trip must demonstrate persistence across store instances:

  ```python
  artifact_id = LocalArtifactStore(root).put(provenance)
  result = LocalArtifactStore(root).get(
      artifact_id,
      expected_source_ref=provenance.observation.source.source_ref,
      served_at=served_at,
  )
  assert result.observation == provenance.observation
  assert result.cache_status == "hit"
  ```

- [x] Implement canonical versioned JSON, bounded verified reads, and exclusive
  publication. Never use replacement writes for existing artifact names.
- [x] Run `uv run --offline --cache-dir /tmp/cms-data-mcp-uv-cache pytest -q`.

Review focus: malformed self-hashed files, altered source/scope, simultaneous
publication, failure before/after publication, and symlink/special-file targets.
Each has filesystem-level tests rather than assertions on implementation text.

## Task 2 — Review and checkpoint

- [x] Independent review of storage, tests, and the contract; reproduce and fix
  material findings with regression tests.
- [x] Run full pytest, Ruff lint/format, strict mypy, scaffold/link validation,
  and the package build. Smoke-test the installed wheel's storage round-trip.
- [x] Update README, architecture, cache/test docs, and PROJECT_STATE.md with
  actual checks and one bounded next task. No commit or publication in this unit.

Completed 2026-10-04. Review required explicit descriptor ownership and validation
of UTC overflow; both are covered by regressions. See [verification](storage-verification.md).
