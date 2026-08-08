# zksato Roadmap

## Repository operating system

Status: **implemented**

- [x] `AGENTS.md` repository-wide engineering contract
- [x] specialist `agents/` playbooks covering every critical platform domain
- [x] reusable `skills/` procedures for implementation, validation, operations, and GitHub maintenance
- [x] comprehensive project documentation index and contracts
- [x] architecture decision records for risk, persistence, reconciliation, AI, TFEX, and deployment boundaries
- [x] GitHub CODEOWNERS, PR template, issue templates, Dependabot, release categories, Copilot instructions, and governance workflow
- [x] explicit feature matrix and production completion execution plan

## Current release — v0.2 automation dashboard

Status: **implemented**

- [x] FastAPI control plane and responsive dashboard
- [x] deterministic risk engine
- [x] paper broker with fill simulation
- [x] paper cash/portfolio/P&L accounting
- [x] quote ingestion and synthetic demo feed
- [x] EMA crossover, RSI reversion and breakout strategies
- [x] strategy-driven bot lifecycle
- [x] protective paper stop-loss / take-profit exits
- [x] price alerts and webhook notifications
- [x] backtesting engine
- [x] signals and audit trail
- [x] Settrade Open API v2 equity adapter
- [x] paper / sandbox / live execution modes
- [x] explicit live confirmation boundary
- [x] autonomous live execution blocked at service and API layers
- [x] Docker runtime and GitHub Actions CI

## Phase A — Durable state and broker reconciliation

Priority: **highest before production**

- [ ] PostgreSQL schema and migrations
- [ ] durable orders, fills, positions, signals and risk decisions
- [ ] durable idempotency keys that survive restarts
- [ ] Settrade order/deal reconciliation worker
- [ ] change/replace order adapter with SDK-version integration tests
- [ ] retry taxonomy with bounded exponential backoff
- [ ] explicit `unknown/needs-reconciliation` order state for ambiguous timeouts
- [ ] startup recovery from broker state
- [ ] transactional outbox for notifications and audit export
- [ ] Redis distributed locks/cache only after durable semantics are proven

**Exit criteria:** restarting any process cannot duplicate an accepted order, and local state converges to broker state after failures.

## Phase B — Native Settrade market data

- [ ] Settrade v2 realtime price subscriptions
- [ ] bid/offer subscriptions
- [ ] reconnect/backoff supervisor
- [ ] stale-feed circuit breaker
- [ ] duplicate/out-of-order/gap detection
- [ ] SET / SET50 / SET100 symbol-universe loader
- [ ] TFEX contract-universe loader
- [ ] OHLCV persistence and deterministic replay
- [ ] historical data adapter
- [ ] scanner ranking for price, value, volume and relative volume
- [ ] ATR / ADX / Bollinger / VWAP indicators
- [ ] WebSocket/SSE fan-out for dashboard clients

**Exit criteria:** strategies run from timestamped trusted Settrade inputs, stale feeds stop execution, and recorded sessions can be replayed.

## Phase C — Security and operator authorization

- [ ] authenticated users and secure sessions
- [ ] read-only / strategy-operator / order-approver / risk-admin / platform-admin / auditor RBAC
- [ ] CSRF, CORS, rate limiting, session expiry/revocation
- [ ] move from reusable live confirmation token toward short-lived intent-bound approval records
- [ ] account allow-list and approval audit
- [ ] Vault/KMS or equivalent managed secret integration
- [ ] secret rotation runbook and redaction tests
- [ ] TLS reverse proxy and hardened exposed deployment profile

**Exit criteria:** every external mutation is authenticated, authorized server-side, auditable, least-privilege, and cannot bypass risk.

## Phase D — TFEX execution

- [ ] dedicated derivatives domain model
- [ ] LONG / SHORT and OPEN / CLOSE / AUTO position semantics
- [ ] contract multiplier/tick/expiry/rollover metadata
- [ ] derivatives account/margin snapshot
- [ ] derivatives order placement/cancel/change
- [ ] stop-order parameters
- [ ] margin and call-force risk controls
- [ ] daily settlement/P&L semantics
- [ ] SET and TFEX strategy/risk isolation with consolidated exposure view
- [ ] UAT certification for open/close long/short, partial fills, margin rejection, rollover

## Phase E — Advanced strategy research

- [ ] strategy plugin registry
- [ ] ATR position sizing
- [ ] volatility targeting
- [ ] trailing stops
- [ ] scale-in / scale-out policies
- [ ] multi-timeframe signals
- [ ] commission, slippage and partial-fill models
- [ ] walk-forward and out-of-sample testing
- [ ] parameter/version registry
- [ ] strategy comparison and tear-sheet reports
- [ ] paper-vs-backtest drift reports
- [ ] deterministic historical event replay

## Phase F — Advanced risk

- [ ] gross and net exposure limits
- [ ] per-symbol and sector concentration limits
- [ ] maximum open orders and order-rate limits
- [ ] consecutive broker/API error circuit breaker
- [ ] trading-session and auction-state policy
- [ ] price-band, tick-size, spread and slippage validation
- [ ] stale-quote and unknown-session fail-closed guards
- [ ] margin buffers and TFEX expiry restrictions
- [ ] operator approval queue and optional four-eyes production approval
- [ ] versioned risk policies with persisted reason codes and evaluated inputs

## Phase G — Observability, resilience, and operations

- [ ] Prometheus-compatible metrics
- [ ] OpenTelemetry traces
- [ ] Grafana dashboards and actionable alerts
- [ ] structured JSON logs and Loki/equivalent
- [ ] stable correlation IDs from signal → risk → order → broker → fill
- [ ] dependency/image/SBOM/code scanning
- [ ] PostgreSQL backup/restore verification
- [ ] disaster recovery drills and measured RPO/RTO
- [ ] SLOs for feed freshness, reconciliation, API health, and audit completeness
- [ ] load/performance tests for feeds, orders, reconciliation, and backtests
- [ ] broker/feed/DB/Redis/network fault-injection scenarios

## Phase H — AI-assisted research

AI stays outside the trusted execution boundary.

- [ ] market-context and approved-news summarization
- [ ] scanner explanations
- [ ] strategy research assistant
- [ ] anomaly detection and incident summaries
- [ ] natural-language read-only portfolio queries
- [ ] AI proposal queue with deterministic typed validation
- [ ] model/provider/version audit metadata where material
- [ ] explicit authenticated human approval for any proposed live action

## Controlled production rollout

Production promotion is operational, not a frontend switch:

1. Complete Phase A durable state/reconciliation and Phase C auth/RBAC/secrets.
2. Validate Settrade SDK configuration in UAT (`environment=uat`).
3. Run recorded/replay tests, paper trading, and broker UAT scenarios.
4. Reconcile every sandbox order/fill/position against broker state.
5. Enable authenticated manual-confirmation production mode only.
6. Start with conservative server-side limits and minimal exposure.
7. Verify stale-feed, risk, alert, reconciliation, backup, and kill-switch behavior.
8. Increase limits only from reviewed evidence and documented release gates.

Autonomous live-money execution remains intentionally outside the supported trust boundary.

See `docs/FEATURE-MATRIX.md` for current status and `docs/EXECUTION-PLAN.md` for the ordered completion plan.
