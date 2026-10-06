# ADR 002: Finish the fixed aggregate workflow before widening analytics

Status: accepted, 2026-10-04.

## Context

The approved CMS contract provides one California/primary-cardiology scalar count.
It excludes personal records and uninvestigated narrower aggregates. The existing
models and persistent store already preserve that exact scope.

## Decision

Complete discovery, metadata, schema, retrieval, validation, query, CSV export and
provenance around that view. Keep the synthetic shortcut. Use direct typed filters
and projection over the single normalized row. Store bounded immutable JSON
records and CSV files; resolve their full parent chain on provenance/export reads.
Default server startup is offline; live access requires an operator flag.

## Alternatives and consequences

DuckDB would be appropriate for larger approved tables but adds dependency and
SQL boundaries without benefit for one row. Parquet offers little value at this
size; CSV gives an inspectable artifact. General discovery, grouping, city/counties,
version comparison and additional sources require separate evidence and contracts.

This delivers a complete, reproducible workflow while keeping its analytical
scope explicit. It demonstrates MCP interfaces, HTTP source checks, deterministic
validation, immutable storage and lineage without claiming a general data platform.
