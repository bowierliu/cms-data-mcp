# Synthetic upstream fixtures

`catalog_entry.json` is hand-authored metadata for a fictional dataset. The
`.invalid` URL cannot be mistaken for a CMS endpoint. Its release, fields, and
counts are invented for testing. Real CMS dataset identity and documentation
belong in `docs/datasets.md`, not in this synthetic payload.

Add API failures and version changes when the corresponding contract is tested.
Never record responses containing real clinician names, NPIs, addresses, or
other personal records.
