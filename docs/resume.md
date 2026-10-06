# Resume and interview evidence

These bullets describe the implemented first release, not the broader roadmap:

- Built a Python MCP server with nine typed tools for curated CMS discovery,
  bounded aggregate retrieval, deterministic validation, constrained querying,
  CSV export, and verifiable provenance.
- Implemented source-verified HTTP acquisition with deadlines, bounded retries,
  redirect and response checks, immutable content-addressed caching, and parent
  integrity validation across derived results.
- Tested the workflow with 286 offline cases spanning domain models, real files,
  simulated HTTP, SDK sessions, and stdio processes; verified the installed wheel
  and a permitted live CMS aggregate end to end.
- Evaluated eight user-intent scenarios using a fresh agent and recorded tool
  traces, observing correct final outcomes with one field-name recovery case.

Explain the scope immediately: one fixed California primary-cardiology aggregate,
record counts rather than unique people, no personal rows, no county inference,
no verified immutable publisher release, and no production deployment.

Useful interview topics:

1. Why MCP is an agent interface while deterministic code supplies the facts.
2. Why an enrollment/location record differs from a unique clinician.
3. Why content hashes, publisher integrity and data quality are distinct claims.
4. Why source selection, retrieval, validation, query, export and serving need
   separate timestamps and linked identities.
5. Why typed one-row filtering is sufficient here, and when DuckDB would become
   useful for a larger approved analytical view.
6. How corruption, source drift, unavailable data, unsupported geography and
   invalid arguments fail without silently substituting another result.

Do not claim generalized CMS search, row-level ingestion, historical comparison,
DuckDB/Snowflake implementation, clinical validation, production scale, a public
GitHub release, or cross-model reliability. [Verification](release-verification.md)
and [agent evaluation](agent-evaluation.md) provide the evidence behind these bullets.
