# Database design

PostgreSQL is the durable operational and research state store when `ZKSATO_DATABASE_URL` is configured. Managed migrations are applied in lexical order before application rollout; SQLAlchemy `create_all()` remains a local/bootstrap guard.

## Migrations

- `migrations/0001_core.sql` — v0.3 core operational baseline
- `migrations/0002_priority_state.sql` — v0.4 order-event/fill/risk/account/research history

Already-deployed migrations are immutable. New schema work appends a new numbered migration.

## Implemented durable state

| Table | Purpose |
|---|---|
| `orders` | local/broker IDs and typed order payload |
| `order_events` | append-oriented order/reconciliation lifecycle evidence |
| `fills` | durable fill records with broker-fill deduplication |
| `risk_evaluations` | deterministic risk outcome, inputs, actor, and policy version |
| `account_snapshots` | point-in-time account/equity/P&L snapshots |
| `quotes` | latest trusted quote snapshot by symbol |
| `market_bars` | historical OHLCV bars keyed by symbol/timeframe/timestamp |
| `signals` | generated deterministic strategy signals |
| `strategy_versions` | strategy/configuration versions and hash |
| `strategy_runs` | replay/walk-forward research run evidence |
| `audit_events` | operational/security/trading audit records including hash-chain fields in payload |
| `alerts` | price-alert state |
| `idempotency_keys` | unique client-order claims surviving process restart |
| `outbox` | durable notification delivery queue |
| `runtime_state` | paper-account state and broker-reconciliation readiness |
| `live_approvals` | short-lived intent-bound privileged approval records |
| `schema_migrations` | managed migration ledger |

Paper holdings are persisted in the paper-account runtime payload; independent durable fill history permits expected-position reconstruction and session comparison against the broker portfolio.

## Correctness constraints

- `client_order_id` uniqueness is an execution-safety boundary and must survive restart.
- Broker fill IDs are unique where supplied; reconciliation uses deterministic fallback identifiers when needed.
- Ambiguous broker outcomes retain their idempotency claim and force reconciliation readiness false.
- Broker-facing operation remains closed until reconciliation converges with no unresolved orders.
- Privileged approval records are single-use and fingerprint the complete order intent.
- Paper cash/holdings/P&L state restores before new simulated fills.
- Audit records are append-oriented and include hash-chain material; APIs redact sensitive material.
- Research bars, versions, and runs are durable evidence but never authorize broker actions.
- Broker state remains the external source of truth for sandbox/production reconciliation.

## Transactions and concurrency

PostgreSQL unique constraints provide restart-safe idempotency. Redis may coordinate cross-process work such as reconciliation locks and abuse protection, but Redis is not the trading system of record. Correctness must remain recoverable from PostgreSQL plus broker state.

**SQLite concurrency:** Uses native `ON CONFLICT DO UPDATE` for both PostgreSQL and SQLite dialects to avoid SELECT→INSERT race conditions in the upsert path.

## Shared Local Infrastructure (`zpostgresql` and `zredis`)

When integrating with local shared infrastructure:
- **PostgreSQL (`zpostgresql`)**: Accessible over container network `zPostgreSQL_network` (or host bridge at `172.26.0.5:5432` / `localhost:5432` if port forwarded).
  - Database URL format: `postgresql+psycopg://<user>:<password>@zpostgresql:5432/<db_name>` (in Docker) or `postgresql+psycopg://<user>:<password>@172.26.0.5:5432/<db_name>` (from host).
- **Redis (`zredis` / `zRedis`)**: Accessible over `zPostgreSQL_network` (or host bridge at `172.26.0.3:6379`). Uses Redis 7.4 ACL authentication.
  - Redis URL format: `redis://<username>:<password>@zredis:6379/<db_index>` (in Docker) or `redis://<username>:<password>@172.26.0.3:6379/<db_index>` (from host).

## Public Ingress and Endpoints (`https://zksato.zeaz.dev/*`)

In production and reverse-proxy deployment environments:
- **Operator Portal / UI**: `https://zksato.zeaz.dev/`
- **TradingView Market Terminal**: `https://zksato.zeaz.dev/v1/market/terminal`
- **Health Check & Readiness**: `https://zksato.zeaz.dev/health`, `https://zksato.zeaz.dev/livez`, `https://zksato.zeaz.dev/readyz`
- **Native Agent OS Skills & Execution**: `https://zksato.zeaz.dev/v1/agent-os/skills`, `https://zksato.zeaz.dev/v1/agent-os/execute`
- **Prometheus Telemetry**: `https://zksato.zeaz.dev/metrics`
- **Vite Lite Dashboard**: `https://zksato.zeaz.dev/dash/`
- **API Documentation**: `https://zksato.zeaz.dev/docs`, `https://zksato.zeaz.dev/openapi.json`
- **Auth Session & RBAC**: `https://zksato.zeaz.dev/v1/auth/session`, `https://zksato.zeaz.dev/v1/auth/me`
- **TradingView Webhooks**: `https://zksato.zeaz.dev/v1/webhooks/tradingview`

Ensure `ZKSATO_ALLOWED_ORIGINS` and `ZKSATO_ALLOWED_HOSTS` include `https://zksato.zeaz.dev` and `zksato.zeaz.dev`.

## Backup and recovery

Use `scripts/backup_postgres.sh` and `scripts/restore_postgres.sh` only against an explicitly selected database. After restore, apply every migration, start with broker-facing operation disabled, verify health/audit state, and complete reconciliation before normal operation. The full procedure is in `docs/DR-RUNBOOK.md`.
