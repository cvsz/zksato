# zksato Roadmap

## Current release — v0.4 P0-P6 source completion

All repository-controlled P0-P6 work is implemented or represented by fail-closed control-plane gates. Items that require a broker account, legal/operational approval, production infrastructure, or measured deployment evidence remain explicitly external and cannot be self-certified by source code.

### P0 — Durable correctness

- [x] PostgreSQL/SQLAlchemy system of record for orders, order events, fills, risk evaluations, account snapshots, signals, audit, alerts, idempotency, outbox and historical bars
- [x] versioned migrations `0001_core.sql` and `0002_priority_state.sql`
- [x] restart-safe `client_order_id` uniqueness
- [x] persistent paper state and broker-reconciliation readiness
- [x] ambiguous place/cancel outcomes fail into `needs_reconciliation`
- [x] reconciliation convergence gate before sandbox/live broker mutation
- [x] durable fill/order-event capture
- [x] optional Redis distributed coordination with local safe fallback
- [x] PostgreSQL + Redis CI services and migration validation
- [x] restart/recovery/idempotency/reconciliation tests

### P1 — Trusted market data and deterministic risk

- [x] supervised Settrade realtime subscriptions with reconnect backoff
- [x] quote freshness, sequence-gap and out-of-order diagnostics
- [x] stale-feed execution guard
- [x] trusted account/portfolio-derived risk context
- [x] gross, net, symbol and sector exposure guards
- [x] open-order, daily-order, daily-loss, drawdown, notional and spread limits
- [x] account allow-list
- [x] optional exchange-session enforcement
- [x] trusted instrument registry for tick-size and price-band checks
- [x] one-time intent-bound live approvals remain downstream of deterministic risk

### P2 — Security and operator controls

- [x] API-key RBAC with separate reader/strategy/order/risk/auditor/admin roles
- [x] HMAC-signed expiring HttpOnly sessions
- [x] CSRF enforcement for session-authenticated mutations
- [x] CORS, trusted-host, CSP, HSTS and browser security headers
- [x] Redis-coordinated rate limiting when Redis is configured
- [x] server-side secret-file loading and rotation runbook
- [x] tamper-evident audit hash chain
- [x] recursive sensitive-data redaction for audit API output
- [x] four-eyes live approval option

### P3 — TFEX isolation and semantics

- [x] dedicated LONG/SHORT and OPEN/CLOSE/AUTO domain
- [x] account/portfolio/order read gateway
- [x] contract metadata registry with series, multiplier, tick, expiry and settlement metadata
- [x] contract-count, margin, stale-data, tick-size and expiry-window risk controls
- [x] settlement P&L helper
- [x] sandbox/UAT-only TFEX mutation boundary
- [ ] installed-SDK and broker-account TFEX behavior certified in Settrade UAT — **external evidence required**

### P4 — Observability, resilience and recovery

- [x] Prometheus metrics for HTTP, order/risk, reconciliation, feed freshness, outbox and coordination
- [x] correlation context and JSON logging
- [x] optional OpenTelemetry exporter
- [x] Prometheus scrape/alert configuration
- [x] SLO definition
- [x] PostgreSQL backup/restore scripts and DR runbook
- [x] bounded load probe
- [x] broker/reconciliation fail-closed behavior
- [ ] production alert delivery, restore drill, RPO/RTO measurement and sustained load evidence — **deployment evidence required**

### P5 — Strategy research and promotion

- [x] durable OHLCV bar storage
- [x] deterministic historical replay using the production strategy engine
- [x] commission/slippage-aware backtesting
- [x] market-session-aware replay/walk-forward when session enforcement is enabled
- [x] train/out-of-sample walk-forward reporting
- [x] strategy/version registry and code/config hash
- [x] promotion gates from research to paper to UAT to manual-live canary
- [x] paper/backtest drift reporting primitive
- [ ] strategy-specific performance evidence — **research evidence, not a code-completion claim**

### P6 — Controlled production rollout

- [x] machine-readable production-readiness report
- [x] external evidence model for broker/legal/UAT/TLS/secrets/backup/monitoring/canary approval
- [x] fail-closed one-order manual canary plan
- [x] durable-fill versus broker-position session reconciliation service
- [x] UAT certification probe and runbook
- [x] production readiness, secrets, DR and SLO runbooks
- [ ] broker permission and legal/operational sign-off — **external**
- [ ] Settrade UAT certification evidence — **external**
- [ ] production TLS/managed-secret/monitoring/backup drill evidence — **external**
- [ ] explicitly authorized minimal live canary — **external operator action**

## Non-negotiable invariant

**Autonomous live-money execution remains forbidden by design.** AI, agents and strategies may research, rank, explain, paper-trade and operate in broker UAT, but a live equity mutation requires deterministic risk plus explicit operator authorization. TFEX mutation remains UAT-only until its external certification gate is completed.
