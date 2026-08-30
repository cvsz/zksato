# Feature matrix

Status meanings: **Implemented** = repository code exists and is covered by automated/source validation; **External gate** = code/control exists but proof depends on broker, deployment, GitHub plan/settings, or operator evidence; **Intentionally unsupported** = prohibited by the risk model.

| Area | Capability | Status | Notes |
| --- | --- | --- | --- |
| Trading | Paper market/limit lifecycle | Implemented | market, resting limit, later-quote match, fill, partial fill, cancel |
| Trading | Paper price improvement / per-quote partial-fill cap | Implemented | deterministic simulator; not exchange queue simulation |
| Trading | Restart-safe paper recovery/client IDs | Implemented | durable with SQL store |
| Trading | Portfolio/P&L recovery | Implemented | persistent cash/holdings/realized P&L |
| Trading | Settrade v2 equity adapter | Implemented | broker UAT certification remains external |
| Trading | CCXT multi-exchange adapter | Implemented | Binance, Binance TH, KuCoin, OKX, Bybit spot paper/sandbox |
| Trading | Prediction market engine & risk | Implemented | synthetic feeds, directional residuals, complete set cost |
| Trading | CPMM liquidity pool & slippage | Implemented | non-linear depth price impact, basis-point slippage, swap executions |
| Trading | Native Agent OS & sandboxed sub-accounts | Implemented | isolated collateral budgets, zero-withdrawal enforcement, skill hub |
| Trading | Confirmed manual live equity boundary | Implemented | deterministic risk + one-time approval |
| Trading | Autonomous live-money execution | Intentionally unsupported | permanent safety invariant |
| Execution | Durable idempotency | Implemented | `client_order_id` uniqueness |
| Execution | Incremental fill ledger | Implemented | cumulative broker snapshots converted to new-fill deltas |
| Execution | Reconciliation fail-closed gate | Implemented | unresolved orders keep execution gate closed |
| Execution | Order identity preservation | Implemented | reconciliation/cancel retain local economic intent |
| Execution | Order detail/filter/cancel-open API | Implemented | bulk action only cancels already-open orders |
| Execution | TradingView webhook ingestion | Implemented | HMAC-SHA256 authenticated webhook with automated order/signal dispatch |
| Execution | Telegram notification dispatcher | Implemented | asynchronous real-time markdown trade and alert delivery |
| UI | Next.js 16 multilingual operator dashboard | Implemented | EN, TH, JA, ZH support, Lightweight Charts, risk gauges |
| UI | Dark TradingView Market Terminal | Implemented | read-only charting terminal with strict CSP |
| Market data | External quote ingestion/demo feed | Implemented | paper/demo and API ingestion |
| Market data | Supervised Settrade realtime bridge | Implemented | UAT evidence external |
| Market data | Durable OHLCV/scanner | Implemented | research/strategy support |
| Market calendar | Recurring sessions/weekends | Implemented | timezone-aware |
| Market calendar | Operator holiday/special-date overrides | Implemented | official calendar verification external |
| Market calendar | Session explanation API | Implemented | source/reason/session list |
| Strategy | EMA/SMA cross | Implemented | deterministic |
| Strategy | RSI/Bollinger reversion | Implemented | deterministic |
| Strategy | Momentum/MACD/breakout | Implemented | deterministic |
| Strategy | Video-derived PA breakout/retest planner | Implemented | OHLC/ATR planner; research-only and non-executing |
| Strategy | Bounded virtual stop ladder | Implemented | hard trigger/quantity caps, fixed size, dedupe keys, no martingale |
| Strategy | Symmetric video-grid reproduction | Implemented | generic/TFEX research only; rejected for SET-equity profile |
| Strategy | Video-EA virtual cycle runtime | Implemented | durable snapshot/recovery, arm/trigger/dedupe/pause/invalidate/basket-boundary/reset; no broker calls |
| Strategy | MQL5 video-derived reference EA | Implemented | Strategy Tester/demo only; volume/tick/stops/freeze/session/expiry/retcode/restart hardening; real-account initialization is blocked |
| Indicators | SMA/EMA/RSI/ATR/ADX/Bollinger/VWAP | Implemented | deterministic |
| Indicators | MACD/rate-of-change/realized volatility | Implemented | deterministic |
| Research | Cost/slippage backtest | Implemented | fees/slippage modeled |
| Research | Backtest analytics | Implemented | closed trades, gross P/L, profit factor, fees, exposure, buy/hold |
| Research | Walk-forward/OOS | Implemented | session-aware split plus rolling windows |
| Research | Parameter sweep and seeded stress analysis | Implemented | bounded combinations, Monte Carlo trade ordering, grid-whipsaw/gap replay |
| Research | Cost sensitivity and maximum-exposure heatmap | Implemented | spread/slippage/commission matrix and bounded basket exposure |
| Research | Strategy/version registry and run history | Implemented | durable with SQL store and immutable evidence hash |
| Research | Drift/promotion evidence gates | Implemented | no broker authority |
| Research | Trading-video evidence extractor | Implemented | ffprobe metadata + deterministic timestamped frames; no media committed |
| Risk | Deterministic trusted pre-trade RiskEngine | Implemented | stale feed/exposure/inventory/loss/session/reference controls |
| Risk | Property-based fail-closed invariants | Implemented | safety properties in CI |
| Security | RBAC/session/CSRF/browser hardening | Implemented | server-side authorization |
| Security | Intent-bound four-eyes approval | Implemented | live boundary |
| Security | Tamper-evident/redacted audit trail | Implemented | readiness verifies chain |
| Operations | Bot start/pause/resume/stop/tick | Implemented | live auto-execute prohibited |
| Operations | Liveness/readiness | Implemented | persistence/coordination/reconciliation/audit checks |
| Operations | Request correlation response ID | Implemented | generated or propagated `X-Request-ID` |
| Operations | Notification durable outbox | Implemented | failed item does not block unrelated batch items |
| Operations | Account snapshot history | Implemented | auditor/admin endpoint |
| TFEX | Isolated domain/risk/UAT mutation | Implemented | production mutation unavailable |
| TFEX | Real broker UAT certification | External gate | credentials/account/broker evidence required |
| Persistence | PostgreSQL durable system of record | Implemented | migrations validated on PostgreSQL 16 |
| Coordination | Redis distributed coordination | Implemented | PostgreSQL remains correctness boundary |
| Observability | Metrics/logging/optional OTel/SLO | Implemented | production delivery evidence external |
| DR | Backup/restore automation and ephemeral drill | Implemented | checksum/corruption/sentinel/timing evidence |
| DR | Production restore/RPO/RTO evidence | External gate | measured externally |
| Performance | Bounded hardened-container SLO probe | Implemented | JSON evidence |
| CI | Python 3.11-3.14 + Postgres/Redis | Implemented | migrations/dependencies/tests |
| CI | Branch coverage ratchet | Implemented | floor 65% |
| Quality | Ruff format/lint and mypy | Implemented | source/scripts |
| Quality | OpenAPI safety contract | Implemented | critical control paths required; research EA controls paper-only; live TFEX rejected |
| Quality | Package/twine/version identity | Implemented | clean installation verified |
| Quality | Runtime dependency license policy | Implemented | isolated inventory |
| Security automation | pip-audit/Bandit/Gitleaks | Implemented | plus secret-pattern scanning |
| Workflow security | immutable SHA pins/actionlint/yamllint/zizmor | Implemented | unsafe patterns rejected |
| Container | Minimal non-root hardened image | Implemented | read-only/no-capabilities/no-new-privileges tests |
| Container security | Trivy CVE gate + CycloneDX SBOM | Implemented | fixed CRITICAL findings block |
| Supply chain | Multi-arch GHCR + release verification | Implemented | digest/checksums/provenance/SBOM |
| GitHub automation | PR policy/labeling/Dependabot/repository health | Implemented | capability report read-only |
| GitHub security | CodeQL/Dependency Review/Secret Protection | External gate | private-repo plan/settings dependent |
| GitHub protection | environments/ruleset/merge queue | External gate | plan/settings dependent |
| Production | Machine-readable readiness + one-order canary plan | Implemented | non-executing/non-autonomous |
| Production | Broker/legal/UAT/TLS/secrets/monitoring/DR/incident/rollback/capacity/time-sync/failover/retention/release evidence | External gate | source cannot certify operational facts |
