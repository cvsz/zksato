# zksato Roadmap

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
- [ ] Redis distributed locks and cache
- [ ] idempotency keys that survive restarts
- [ ] Settrade order/deal reconciliation worker
- [ ] change/replace order adapter with SDK-version integration tests
- [ ] retry taxonomy with bounded exponential backoff
- [ ] startup recovery from broker state
- [ ] outbox pattern for notifications and audit export

**Exit criteria:** restarting any process cannot duplicate an accepted order, and local state converges to broker state after failures.

## Phase B — Native Settrade market data

- [ ] Settrade v2 realtime price subscriptions
- [ ] bid/offer subscriptions
- [ ] reconnect/backoff supervisor
- [ ] stale-feed circuit breaker
- [ ] SET / SET50 / SET100 symbol-universe loader
- [ ] TFEX contract-universe loader
- [ ] OHLCV persistence
- [ ] historical data adapter
- [ ] scanner ranking for price, value, volume and relative volume
- [ ] ATR / ADX / Bollinger / VWAP indicators
- [ ] WebSocket/SSE fan-out for dashboard clients

**Exit criteria:** strategies run from timestamped Settrade inputs, stale feeds stop execution, and recorded sessions can be replayed.

## Phase C — TFEX execution

- [ ] derivatives broker contract
- [ ] LONG / SHORT and OPEN / CLOSE / AUTO position semantics
- [ ] derivatives account/margin snapshot
- [ ] derivatives order placement/cancel/change
- [ ] stop-order parameters
- [ ] contract rollover rules
- [ ] margin and call-force risk controls
- [ ] SET and TFEX strategy isolation

## Phase D — Advanced strategy research

- [ ] strategy plugin registry
- [ ] ATR position sizing
- [ ] volatility targeting
- [ ] trailing stops
- [ ] scale-in / scale-out policies
- [ ] multi-timeframe signals
- [ ] commission, slippage and partial-fill models
- [ ] walk-forward testing
- [ ] parameter/version registry
- [ ] strategy comparison and tear-sheet reports
- [ ] paper-vs-backtest drift reports

## Phase E — Advanced risk

- [ ] gross and net exposure limits
- [ ] per-symbol and sector concentration limits
- [ ] maximum open orders
- [ ] consecutive broker/API error circuit breaker
- [ ] trading-session and auction-state policy
- [ ] price-band and tick-size validation
- [ ] stale-quote and spread guards
- [ ] account allow-list
- [ ] operator approval queue
- [ ] four-eyes production approval option

## Phase F — Security and operations

- [ ] authenticated users and RBAC
- [ ] read-only / operator / risk-admin roles
- [ ] CSRF and hardened browser session controls
- [ ] Vault/KMS secret integration
- [ ] TLS reverse proxy
- [ ] Prometheus metrics
- [ ] OpenTelemetry traces
- [ ] Grafana dashboards and alerts
- [ ] structured JSON logs and Loki
- [ ] dependency/image/SBOM scanning
- [ ] database backup/restore verification
- [ ] disaster recovery runbooks and SLOs

## Phase G — AI-assisted research

AI stays outside the trusted execution boundary.

- [ ] market-context and news summarization
- [ ] scanner explanations
- [ ] strategy research assistant
- [ ] anomaly detection and incident summaries
- [ ] natural-language read-only portfolio queries
- [ ] AI proposal queue with deterministic validation
- [ ] explicit human approval for any proposed live action

## Controlled production rollout

Production promotion should be operational, not a frontend switch:

1. Validate Settrade SDK configuration in UAT (`environment=uat`).
2. Run recorded/replay tests and paper trading.
3. Reconcile every sandbox order against broker state.
4. Enable authenticated manual-confirmation production mode only.
5. Start with conservative server-side limits.
6. Verify stop/alert/kill-switch behavior during canary operation.
7. Increase limits only from reviewed evidence.

Autonomous live execution remains intentionally outside the supported trust boundary.
