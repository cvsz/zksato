# zksato Roadmap

## Phase 0 — Safe foundation

Status: **implemented in initial scaffold**

- [x] Python package and FastAPI control plane
- [x] paper-only execution adapter
- [x] deterministic risk engine
- [x] duplicate `client_order_id` protection in paper mode
- [x] server-side trading-mode guard
- [x] unit tests for core risk/execution boundaries
- [x] environment template with live trading disabled
- [x] architecture documentation
- [x] CI and container baseline

## Phase 1 — Settrade Sandbox integration

Goal: execute and reconcile orders in Settrade UAT/Sandbox without live-money access.

- [ ] Add `SettradeBroker` adapter using official `settrade-v2`
- [ ] Add credential model loaded only from environment/secret store
- [ ] Separate `sandbox` and `live` provider configuration
- [ ] Account information adapter
- [ ] Equity portfolio adapter
- [ ] TFEX/derivatives portfolio adapter
- [ ] Place order
- [ ] Cancel order
- [ ] Change/replace order where supported
- [ ] Query order status and deals
- [ ] Durable client-order-id / broker-order-id mapping
- [ ] Error normalization and retry taxonomy
- [ ] Provider rate-limit/backoff policy
- [ ] Integration tests against Sandbox

**Exit criteria:** no code path can reach production credentials; Sandbox place/cancel/reconcile is repeatable and auditable.

## Phase 2 — Market data and scanner

- [ ] Quote snapshot service
- [ ] Realtime subscription manager
- [ ] reconnect/backoff logic
- [ ] stale-feed detector
- [ ] SET / SET50 / SET100 universes
- [ ] TFEX contract universe
- [ ] OHLCV normalization
- [ ] volume/relative-volume scanner
- [ ] breakout scanner
- [ ] momentum ranking
- [ ] EMA/SMA filters
- [ ] RSI / ATR / ADX indicators
- [ ] scanner API and websocket feed

**Exit criteria:** scanner output is deterministic, timestamped and reproducible from recorded market inputs.

## Phase 3 — Durable state and reconciliation

- [ ] PostgreSQL schema/migrations
- [ ] orders
- [ ] order events
- [ ] deals/fills
- [ ] positions
- [ ] account snapshots
- [ ] signals
- [ ] strategy runs
- [ ] risk decisions
- [ ] audit events
- [ ] Redis locks/cache
- [ ] order reconciliation worker
- [ ] idempotency across process restarts
- [ ] recovery after API/network failure

**Exit criteria:** restarting the service cannot duplicate an accepted order and broker state can be reconstructed.

## Phase 4 — Strategy and backtesting

- [ ] strategy plugin interface
- [ ] signal lifecycle and expiry
- [ ] position sizing by risk per trade
- [ ] commission/slippage model
- [ ] historical data adapter
- [ ] event-driven backtester
- [ ] walk-forward testing
- [ ] parameter-set versioning
- [ ] strategy comparison report
- [ ] paper fill simulator

**Exit criteria:** every strategy promoted to Sandbox has a versioned backtest and paper-trading report.

## Phase 5 — Advanced risk controls

- [ ] maximum gross/net exposure
- [ ] per-symbol allocation
- [ ] sector concentration
- [ ] daily realized/unrealized loss guard
- [ ] rolling drawdown limit
- [ ] maximum open orders
- [ ] market-session policy
- [ ] stale quote / price divergence guard
- [ ] price-band/slippage guard
- [ ] consecutive broker-error breaker
- [ ] global kill switch
- [ ] manual approval mode
- [ ] account allow-list

**Exit criteria:** all critical controls are covered by failure-path tests and can stop execution independently.

## Phase 6 — Dashboard and notifications

- [ ] Next.js dashboard
- [ ] live market/scanner view
- [ ] signal queue
- [ ] approval/reject workflow
- [ ] orders/deals view
- [ ] portfolio/P&L
- [ ] risk status
- [ ] kill switch UI with server-side authorization
- [ ] Telegram/LINE/Discord/email notification adapters
- [ ] daily trading report

## Phase 7 — AI-assisted operations

AI remains outside the trusted execution boundary.

- [ ] market-context summarizer
- [ ] news summarizer from approved sources
- [ ] scanner-result explanation
- [ ] strategy research assistant
- [ ] anomaly detection/reporting
- [ ] natural-language read-only portfolio query
- [ ] tool permissions restricting AI from direct broker mutation
- [ ] auditable human approval for any AI-originated proposed action

## Phase 8 — Production readiness

- [ ] Docker Compose production profile
- [ ] metrics: Prometheus
- [ ] dashboards: Grafana
- [ ] logs: Loki/OpenTelemetry
- [ ] tracing
- [ ] secret manager integration
- [ ] TLS/reverse proxy
- [ ] database backup/restore tests
- [ ] disaster-recovery runbook
- [ ] SLOs and alerts
- [ ] dependency and image scanning
- [ ] protected production environment
- [ ] operational runbooks

## Phase 9 — Controlled live rollout

- [ ] broker/Settrade permissions confirmed
- [ ] production adapter enabled only for an allow-listed account
- [ ] tiny-capital canary strategy
- [ ] manual-confirmation mode first
- [ ] compare expected vs broker fills
- [ ] verify alerts and kill switch
- [ ] gradually increase limits only after reviewed evidence

Live mode should remain a deliberate operational promotion, not a feature flag exposed to an untrusted client.
