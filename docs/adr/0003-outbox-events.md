# ADR-0003: Transactional outbox for reliable domain events

Status: Accepted target

## Decision
Persist important domain changes and outbound event records in the same PostgreSQL transaction; publish asynchronously with idempotent consumers.

## Consequences
Adds worker/cleanup complexity but prevents lost events around process failure.
