# Database design

PostgreSQL is the durable operational state store when `ZKSATO_DATABASE_URL` is configured. `migrations/0001_core.sql` is the v0.3 managed baseline; SQLAlchemy `create_all()` remains a local/bootstrap guard.

## Implemented tables

- `orders` — local/broker IDs plus typed JSON order payload
- `quotes` — latest quote snapshot by symbol
- `signals` — generated strategy signals
- `audit_events` — operational/security/trading audit records
- `alerts` — price-alert state
- `idempotency_keys` — unique client order claims surviving process restart
- `outbox` — durable notification delivery queue
- `runtime_state` — durable paper-account state
- `live_approvals` — short-lived, intent-bound live execution approvals
- `schema_migrations` — managed migration ledger in the SQL migration baseline

## Correctness constraints

- `client_order_id` uniqueness is an execution-safety boundary.
- Live approvals are consumed once and fingerprint the complete order intent.
- Ambiguous broker outcomes retain the idempotency claim until reconciliation.
- Paper cash/holdings/P&L state is restored from `runtime_state` before new fills.
- Broker state remains the external source of truth for sandbox/live reconciliation.

## Migration policy

Production deployments apply numbered SQL migrations before starting the new application revision. Never edit an already deployed migration. Use expand/migrate/contract for incompatible changes and verify backup/restore before destructive schema changes.

## Planned analytical/history schema

The operational tables above are intentionally compact. Durable OHLCV history, fill/deal event history, strategy-version registry, account snapshots and high-volume analytics should be added as append-oriented tables in subsequent migrations rather than overloading the operational JSON records.
