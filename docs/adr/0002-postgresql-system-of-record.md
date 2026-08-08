# ADR-0002: PostgreSQL for durable local trading state

Status: Accepted target

## Decision
Use PostgreSQL for durable orders, events, fills, positions, risk decisions, signals, audit and idempotency. Redis remains ephemeral coordination/cache.

## Consequences
Requires migrations, backup/restore, and transaction design; enables restart-safe correctness and reconciliation.
