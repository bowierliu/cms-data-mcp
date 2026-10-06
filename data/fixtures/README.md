# Synthetic analytical fixtures

`cardiology_counts.csv` contains five invented aggregate rows. It was authored
for cms-data-mcp and is not copied, sampled, or derived from CMS records. All
counts are fictional and represent records, not distinct clinicians. It carries
no person identifiers. Real geography labels are used only as filter examples.

The corresponding synthetic metadata is `tests/fixtures/catalog_entry.json`.
Expected California cardiology rows: San Diego (3), Sacramento (2), and
Los Angeles (0), totaling 5 fictional records. San Diego here is a city label,
not county coverage.
