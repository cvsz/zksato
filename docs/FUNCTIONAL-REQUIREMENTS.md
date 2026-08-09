# Functional requirements

## Market and reference data
FR-001 ingest/store quotes and bars with timestamps and freshness checks.
FR-002 reject or fail closed on stale/unknown automated market state.
FR-003 validate configured sessions, holidays, special sessions, tick sizes, price bands, sectors, and contract metadata.

## Research and strategy
FR-010 run deterministic indicators/strategies, replay, backtests, walk-forward evaluation, version registration, drift evaluation, and promotion evidence.
FR-011 preserve immutable strategy `(name, version)` identity once registered.

## Risk and execution
FR-020 derive trusted pre-trade context server-side.
FR-021 apply deterministic account/session/market-data/exposure/loss/drawdown/notional/order-count/stop/tick/band controls.
FR-022 keep paper, UAT/sandbox, and live boundaries explicit.
FR-023 require explicit one-time operator authorization for live equity mutation; reject autonomous live mutation.
FR-024 preserve order identity and idempotency across retries/restarts.

## Reconciliation and accounting
FR-030 reconcile broker orders/positions and convert cumulative fills into non-duplicated durable fill deltas.
FR-031 block non-paper execution while reconciliation is unresolved or restart freshness has not been re-established.
FR-032 maintain portfolio/account snapshots and audit evidence.

## Platform and operations
FR-040 provide RBAC/session authentication, CSRF, rate limits, trusted host/origin controls, metrics, liveness/readiness, correlation IDs, structured logs, and audit-chain verification.
FR-041 expose operator/research APIs documented by OpenAPI.
FR-042 support migrations, backup/restore, DR drills, release verification, container checks, and production-readiness evidence.

## Notifications
FR-050 deliver operational notifications asynchronously from the trading path; notification failure must not cause money-moving behavior.
