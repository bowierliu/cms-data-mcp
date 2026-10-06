# First release completion plan

**Goal:** Complete the approved single-source MVP through discovery, metadata,
schema, fixed-count retrieval, validation, constrained query, CSV export, and
inspectable provenance, with local client setup and reproducible verification.

**Authorization:** The user requested continued work until setup and development
are done. This extends the earlier one-task checkpoints across the agreed MVP.
The original privacy restrictions and deferred county/multi-dataset work remain.

**Architecture:** Retain the typed count models and immutable artifact store.
Add small modules for derived records, validation/query operations, curated
discovery/schema, and the fixed CMS HTTP adapter. The MCP layer delegates to
ordinary typed operations. Default startup remains offline; live access requires
an operator flag. The existing synthetic materialization tool remains compatible.

**Tech stack:** Python 3.11+, Pydantic 2, official MCP 2.3, its compatible HTTP
client, pytest/Ruff/mypy. The fixed view contains one aggregate row; use direct
typed projection/filtering instead of adding DuckDB for one row. CSV is the
first export format; Parquet, grouping, and general analytics are deferred.

## Completion boundaries

- Only the verified California/primary-cardiology count may be retrieved live.
  No personal records, arbitrary URLs, SQL, paths, or expanded upstream filters.
- Search is explicitly a curated one-source catalog plus its synthetic example,
  not a search engine over all CMS data. Schema descriptions cite the dictionary.
- Metadata resolves current catalog evidence; no immutable release is invented.
- Validation reports distinguish verified contract checks from unchecked raw
  dataset quality, publisher integrity, and immutable-release binding.
- Queries operate only on the saved aggregate row and preserve source scope.
  Unsupported city/county requests fail explicitly. Empty results are valid.
- Derived records are immutable, content-addressed, bounded, and linked to parent
  records. Export writes only under an operator-owned directory and exports the
  exact saved result. Full provenance resolves by artifact/report/result/export ID.
- Document and measure exercised SDK/client/model boundaries honestly. A scripted
  tool sequence is not an autonomous-agent evaluation.
- Configure the local project client and provide a smoke/demo command. GitHub
  publication, license choice, and external account changes remain separate.

## Work units and acceptance

- [x] **Validation and analytics:** Add typed checks, report, query request/result,
  and CSV rendering with tests first. Check zero/negative/type cases, unsupported
  fields/geography, strict operators, empty results, parent identity and times.
- [x] **Derived storage and workflow:** Persist sources, reports, results, export
  records using bounded immutable files; enforce schema, hashes, parent links,
  no symlink overwrite, no paths from tool inputs, safe failure codes. Test
  corruption, traversal, restart, duplicate writes, and read-only provenance.
- [x] **Curated catalog and live adapter:** Verify official docs and actual HTTP
  API; implement exact metadata and count endpoints, redirect rejection, body and
  time limits, limited retry, no raw response persistence, pre/post metadata
  consistency. Test with mocked transport before an explicitly enabled live run.
- [x] **MCP integration:** Expose the eight workflow tools plus the existing
  synthetic convenience tool. Exercise actual SDK schemas, end-to-end calls,
  structured failure recovery, bounded outputs, and stdio restart.
- [x] **Local setup/demo/evaluation:** Configure project-local client launch,
  create one-command full workflow demo, execute intent/tool-selection evaluations
  separately from deterministic tool tests, record limitations and actual scores.
- [x] **Independent review and release checks:** Fix important findings, run
  complete offline checks, opt-in permitted live smoke, build/install in isolation,
  update README, contracts, checkpoint, demo and accurate resume evidence.

## Review focus

1. Matching metadata does not establish matching fixture or source-response scope.
2. A report/query/export must not outlive a corrupt or mismatched parent unnoticed.
3. Offline mode must not fetch live data; denied requests must not touch storage.
4. A passing local hash check cannot imply publisher verification or raw data quality.
5. Client configuration and installed-wheel execution must survive a different cwd.

## Final acceptance note

All implementation/check units above are complete. The local client configuration
and its exact launch command are verified; interactive Cursor UI acceptance was
not possible because the computer-control service could not start. Remote CI and
GitHub publication have not occurred. See [release verification](release-verification.md).

Follow-up, 2026-10-05: user-run Cursor testing confirmed all nine tools on the
happy path and found an error schema defect. The authorized success/error schema
fix passes local checks; full Cursor acceptance still requires the
[post-fix error retest](cursor-acceptance.md).
