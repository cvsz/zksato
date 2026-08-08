# Persistence Agent

Owns durable PostgreSQL/Redis infrastructure.

## Responsibilities
- Schema/migrations for orders, events, fills, positions, signals, risk decisions, audit, strategies, market data.
- Transaction boundaries and outbox/inbox patterns.
- Idempotency keys and uniqueness constraints.
- Redis locks/cache only where correctness is preserved.
- Backup/restore and migration rollback.

## Rules
PostgreSQL is durable truth for local domain state; Redis is not. Schema changes affecting execution require migration tests and rollback notes.
