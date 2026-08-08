# Production completion execution plan

## P0 — Durable correctness
1. PostgreSQL schema/migrations for orders, order events, fills, positions, risk decisions, signals, strategy runs, audit events, account snapshots.
2. Repository layer replacing process-local trading truth.
3. Durable idempotency keys and uniqueness constraints.
4. Broker order/deal reconciliation worker with ambiguous-timeout recovery.
5. Redis coordination only after durable semantics are defined.
6. Restart/crash tests proving no duplicate execution.

**Exit:** process restart and network ambiguity cannot silently duplicate orders; local state converges to broker state.

## P1 — Trusted market data and risk
1. Native Settrade realtime feed with reconnect/backoff/subscription manager.
2. Feed freshness/gap/out-of-order monitoring and stale-feed execution breaker.
3. Expanded risk: gross/net/symbol/sector exposure, session rules, price bands, open-order limits.
4. Dedicated account allow-list and operator approval records.

**Exit:** automation only acts on fresh trusted data and all required risk inputs are available.

## P2 — Security and operator control
1. Authentication, RBAC, secure sessions, CSRF/CORS/rate limiting.
2. Managed secret store integration and rotation runbook.
3. Tamper-evident audit export and sensitive-data redaction tests.
4. Permission-separated read, strategy-control, risk-admin, and order-approval roles.

**Exit:** exposed deployments have authenticated least-privilege control over every mutation.

## P3 — TFEX
1. Contract metadata/series/expiry/rollover.
2. Long/short/open/close semantics and margin.
3. TFEX portfolio/P&L and risk integration.
4. UAT certification for order lifecycle and reconciliation.

## P4 — Observability and resilience
1. Metrics/logs/traces with stable correlation IDs.
2. SLOs and actionable alerts.
3. Backup/restore, recovery drills, DB/Redis/broker outage tests.
4. Performance/load tests and queue/reconciliation lag limits.

## P5 — Strategy research maturity
1. Event-driven historical store/replay.
2. Fees/slippage/session-aware backtests.
3. Walk-forward/out-of-sample reports and parameter registry.
4. Promotion gates from research → paper → UAT.

## P6 — Controlled production rollout
1. Complete broker permissions/legal/operational requirements.
2. Manual-confirmation live canary only.
3. Compare expected vs broker fills/positions daily.
4. Increase limits only from reviewed evidence.

Autonomous live-money execution remains out of scope by design.
