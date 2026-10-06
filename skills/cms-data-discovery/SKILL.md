---
name: cms-data-discovery
description: Use when finding or distinguishing CMS datasets, relevant fields, source coverage, or evidence for the latest release.
---

# CMS data discovery

Turn an information need into an evidence-backed dataset choice. Read the
project's `docs/datasets.md` for the current source candidate and restrictions.

1. Extract the needed population, measure, geography, time period, and row grain.
   Check whether the request would require prohibited personal records.
2. Search official CMS catalogs and documentation. Use search results to locate
   primary pages, not to certify freshness or field semantics.
3. Record publisher dataset ID, title, landing URL, documentation URL, candidate
   distribution, release evidence, coverage period, and observation timestamp.
4. Compare similarly named datasets by population and grain. An NPI enumeration
   file and a Medicare enrollment/location file answer different questions.
5. Resolve `latest` against source release evidence, accounting for archives and
   revisions. Separate publication, modification, coverage, and retrieval dates.
   If evidence conflicts, report unresolved freshness and the next evidence needed.

Return a short candidate table, selected candidate with rationale, required
fields and their evidence, limitations, and next permitted operation. Do not
download data merely to prove discovery.

Example: a catalog snippet dated August and a September archive entry do not
alone establish the newest release of `mj5m-pzi6`. Confirm archive membership
and the actual distribution before resolving a version. A planned update date
is not a published release.

Common mistakes: treating the first search hit as authoritative, replacing an
unavailable official source with a mirror, or promising county coverage from a
city field. Apply `cms-source-validation` when a candidate's authority is in doubt.
