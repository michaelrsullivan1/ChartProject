# ADR 0001: Raw payload storage starts in Postgres

## Status

Accepted

## Context

The project needs a durable archive of untouched provider responses so ingest logic can change without losing source fidelity.

## Decision

The initial implementation stores raw payloads in the `raw_ingestion_artifacts` table.

The schema leaves room for an optional `source_path` so the project can add filesystem copies later if raw volume or backup strategy makes that worthwhile.

## Consequences

- The first ingest pipeline can stay simple and inspectable.
- Raw payload review lives next to ingest run metadata.
- We avoid introducing file layout and lifecycle rules before they are needed.
- Very large payload volumes may justify dual storage later.
