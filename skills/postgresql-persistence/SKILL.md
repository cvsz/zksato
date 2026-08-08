# Skill: PostgreSQL persistence

## Workflow
Model domain records/events → choose keys/constraints → migration → repository adapter → transaction boundaries → outbox where external side effects exist → recovery/reconciliation tests.

## Required constraints
Unique idempotency keys, immutable/auditable order events, referential integrity for orders/fills/risk decisions/signals, UTC timestamps, migration rollback/forward plan.
