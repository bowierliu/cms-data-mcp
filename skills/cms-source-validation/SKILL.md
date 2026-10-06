---
name: cms-source-validation
description: Use when verifying a CMS publisher, dataset identity, distribution URL, release evidence, redirects, or source documentation.
---

# CMS source validation

Validate authority separately from byte integrity and data quality.

For each candidate, report publisher, dataset ID, official landing URL,
distribution URL, final resolved URL, documentation, release evidence, and the
UTC time at which those facts were checked. State unknown values explicitly.

An approved adapter owns the exact HTTPS hosts and paths it may access. Parse
URLs structurally, reject userinfo and unexpected ports, and validate redirects
before following them. A hostname containing `cms.gov` is not enough. Reject
loopback, private/link-local destinations, and undocumented external hosts.
An external distribution requires evidence from the authoritative CMS page and
an explicit adapter policy; never silently allow it through a substring match.

Confirm that title, publisher identifier, fields, release, and documented
population refer to the same dataset. An archive containing multiple datasets
requires confirmation of the selected member. Record release absence as unknown;
an HTTP Last-Modified header is not automatically a release date.

Example: `https://data.cms.gov.example.invalid/file.csv` is not a CMS source.
A third-party mirror claiming identical bytes cannot establish authority. A
locally computed SHA-256 records content identity; publisher checksum comparison
is a separate check and may be unavailable.

Return `verified`, `unresolved`, or `rejected` with evidence and a recovery step.
Verification covers only the stated evidence and time. Do not claim that verified
authority establishes freshness, clinical suitability, or permission to ingest
PII. Follow the project's data restrictions before retrieving rows.
