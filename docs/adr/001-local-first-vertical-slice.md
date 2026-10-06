# ADR 001: One local package and one complete workflow

Status: selected for the scaffold, 2026-10-01.

## Context

cms-data-mcp must demonstrate trustworthy CMS data access and MCP engineering
without an unimplemented framework. The initial workspace contains no project
code and sits inside a separate vault repository.

## Decision

Create a separate project root named `cms-data-mcp`. Use a src-layout Python
package, local stdio transport, one source adapter, embedded DuckDB, and immutable
files plus JSON manifests. Start provenance with the first retrieval, and test a
single synthetic workflow through MCP before broadening source coverage. Keep
the scaffold limited to package metadata, documentation, workflows, and fixtures.

## Why

The same operations can be tested without an agent and exposed through MCP.
Local storage keeps setup understandable. Provenance is part of every result,
so it cannot become an afterthought bolted onto inconsistent interfaces.

## Alternatives considered

A module for every potential tool adds empty abstractions. One large server file
hides domain boundaries. Separate services and a metadata database increase
operations work without helping the first workflow.

## Consequences

The first version is single-process and local. Concurrent multi-user writes,
remote authentication, and scale-out are not promised. Add SQLite only when
manifest lookup or transactional metadata needs justify it. The candidate
clinician source is subject to the strict no-PII constraint; current planning
allows metadata, synthetic records, and verified non-identifying aggregates.
