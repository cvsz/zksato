# Database design

Target: PostgreSQL as durable local trading system of record.

## Required tables
- `accounts`
- `instruments`
- `market_quotes` / partitioned `market_bars`
- `strategies`, `strategy_versions`, `strategy_runs`
- `signals`
- `risk_decisions`
- `order_intents`
- `orders`
- `order_events`
- `fills`
- `positions` / `position_snapshots`
- `account_snapshots`
- `alerts`
- `audit_events`
- `outbox_events`
- `idempotency_keys`
- `operator_approvals`

## Constraints
Unique client idempotency key per account, unique broker-order mapping where applicable, unique broker fill/deal ID, foreign keys across intent/risk/order/fill, UTC timestamps, explicit numeric precision, append-oriented order/audit events.

## Migration policy
Alembic or equivalent migration tooling, forward migration in CI, rollback/restore plan for destructive changes, no ad-hoc production schema edits.

## Transactions
Persist intent/idempotency/risk decision atomically before broker mutation where possible. Persist broker outcome and outbox event atomically. Reconciliation repairs ambiguous outcomes.
