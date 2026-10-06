# Working curated discovery

Question: “Find the CMS dataset containing clinician specialty fields.”

1. `search_datasets(query="clinician specialty")` returns the curated
   `mj5m-pzi6` candidate and its synthetic example. This is not a general catalog
   search and does not certify freshness.
2. `get_dataset_metadata(dataset_id="mj5m-pzi6", release="latest")` fetches and
   validates public metadata when live access is enabled. Offline mode returns
   `LIVE_ACCESS_DISABLED`; use `synthetic-count-v1` to continue offline.
3. Pass its `source_ref` and dataset ID to `get_schema`, with the desired field
   subset. NPI definitions are metadata only; no personal values are fetched.
4. Explain catalog release/modification dates separately from the unknown
   immutable release binding. Metadata is not a validation of underlying rows.

[Tool contracts](../docs/mcp-tools.md) document all inputs and recovery behavior.
The tested live observation and remaining uncertainty are in
[release verification](../docs/release-verification.md).
