# zksato

Risk-first automation, research, paper execution, and operations control plane for SET / TFEX workflows.

zksato separates **market data → deterministic strategy/research → deterministic risk → controlled execution → reconciliation → portfolio/audit**. Paper mode is the default. Settrade Open API v2 stays behind server-side adapters and credentials.

> **Deployment Strategy:** `localhost` (via Docker Compose) is the primary target environment for running all features. Cloud configurations (AWS/GCP via Terraform) in the `deploy/terraform/` directory are intended for backup/failover only.

> **Permanent boundary:** autonomous live-money execution is forbidden. Live equity mutation requires deterministic server-side risk plus explicit operator authorization. TFEX mutation remains sandbox/UAT-only until broker certification.

## v1.0.0 — Production Release & Multi-Exchange Architecture

### Execution, Market, and Prediction Behavior

- FastAPI control plane + responsive dashboard on port `9569` + Next.js 16 operator UI on port `3016`
- PostgreSQL durable orders/events/fills/risk/account snapshots/bars/quotes/signals/alerts/audit/idempotency/outbox/runtime state
- optional Redis coordination/rate-limit state; PostgreSQL remains the correctness boundary
- CCXT multi-exchange spot adapter (Binance, Binance TH, KuCoin, OKX, Bybit) supporting paper/sandbox execution
- Prediction markets module: synthetic probability feeds, complete-set cost calculations, directional residual limits, and guarded live execution gate
- TradingView webhook ingestion with HMAC-SHA256 signature verification and automated alert/signal dispatching
- Telegram asynchronous alert and trade notification delivery
- Dark TradingView Market Terminal with read-only sandbox mode and CSP headers
- restart-safe paper cash/holdings/P&L and client-order identity
- paper market orders plus resting limit orders that can match on later quotes
- configurable deterministic per-quote partial fills and quote-side price improvement
- cancellation of partially filled remainders
- cumulative broker snapshots converted to incremental durable fills without double counting
- ambiguous broker outcomes fail closed and require reconciliation
- reconciliation preserves local economic order identity and blocks non-paper execution while unresolved
- broker reconciliation readiness is restart-local freshness state and must be re-established after each non-paper process restart
- supervised Settrade realtime feed with reconnect/freshness/gap/out-of-order diagnostics
- Asia/Bangkok recurring sessions plus operator-provided holiday/special-session overrides
- trusted reference metadata for sector, tick-size, and price-band checks

### Strategy and research

Deterministic strategy catalog:
- EMA cross
- SMA cross
- RSI reversion
- Bollinger reversion
- momentum
- MACD cross
- breakout

Indicator library includes SMA, EMA, RSI, ATR, ADX, Bollinger Bands, VWAP, MACD, rate-of-change, and realized volatility.

Research supports durable OHLCV bars, deterministic replay, commission/slippage-aware backtests, walk-forward/OOS evaluation, strategy/version registry, run history, drift evaluation, and promotion evidence gates. Backtests expose drawdown, win rate, closed-trade P&L, gross profit/loss, profit factor, fees, exposure, and buy-and-hold benchmark.

### Risk, security, and operations

- server-derived pre-trade context for money-moving order mutation
- stale-feed/session/spread/position/notional/open-order/daily-order/loss/drawdown/gross/net/symbol/sector/account/tick/price-band checks
- portfolio VaR/CVaR with linear interpolation, concentration proxy, allocation limits
- API-key RBAC, HMAC-signed HttpOnly sessions with automatic pruning, CSRF, CORS/trusted hosts, CSP/HSTS, secret-file loading, redaction, hash-linked audit
- one-time intent-bound live approvals with optional four-eyes separation
- bot start/pause/resume/stop/tick controls
- order detail/filtering and safe cancel-all-open-by-symbol operation
- account snapshot history and market-session diagnostics
- liveness `/livez`, readiness `/readyz`, health `/health`, metrics `/metrics`
- propagated/generated `X-Request-ID` correlation identifiers
- durable notification outbox that does not let one poison message block unrelated notifications
- order archival (bounded memory with configurable max)
- Prometheus + JSON logs + optional OpenTelemetry + SLO/DR/performance/release assurance
- separate TFEX domain with UAT-only mutation

## Environments

- **dev** — local development, paper mode by default, optional sandbox credentials
- **test** — CI/ephemeral, paper/sandbox only, no production secrets
- **uat** — broker sandbox certification, Thu/Fri 09:00-17:00 Thailand time, Equity Day + Derivatives Day/Night only
- **prod** — production live trading, requires full external evidence and operator authorization

For environment-specific unlock/release procedures, see [`docs/UNLOCK-RELEASE.md`](docs/UNLOCK-RELEASE.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
ruff check .
ruff format --check .
pytest -m "not uat and not performance"
uvicorn zksato.api:app --reload --port 9569
```

Docker Compose:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:9569/readyz
```

## Paper execution simulator

```dotenv
ZKSATO_PAPER_MATCH_RESTING_LIMITS=true
ZKSATO_PAPER_MAX_FILL_QUANTITY_PER_QUOTE=0
ZKSATO_PAPER_PRICE_IMPROVEMENT=true
```

`0` means no deterministic per-quote fill cap. A positive value produces reproducible partial fills across quotes. This is a simulator; it does **not** claim to reproduce exchange queue priority or real liquidity.

## Market calendar

```dotenv
ZKSATO_MARKET_TIMEZONE=Asia/Bangkok
ZKSATO_EQUITY_SESSIONS=09:30-12:30,14:00-16:30
ZKSATO_EQUITY_HOLIDAYS=2026-01-01,2026-04-13
ZKSATO_EQUITY_SPECIAL_SESSIONS_JSON={"2026-12-31":"09:30-12:00"}
ZKSATO_ENFORCE_MARKET_SESSIONS=true
```

The repository deliberately does not hard-code an official exchange holiday calendar. Operators must load and verify the target-period calendar.

## Authentication

```dotenv
ZKSATO_AUTH_REQUIRED=true
ZKSATO_API_KEYS=risk-key:risk_admin;order-key:order_approver;reader-key:read_only
ZKSATO_SESSION_SECRET=replace-with-a-long-random-secret
ZKSATO_CSRF_REQUIRED=true
```

Machine clients can use `X-API-Key` or Bearer credentials. Browsers can exchange a machine credential through `POST /v1/auth/session` for a signed, expiring HttpOnly session plus CSRF token.

## API groups

- Platform/auth: `/health`, `/livez`, `/readyz`, `/metrics`, `/v1/config`, `/v1/auth/*`, `/v1/dashboard`
- Market/reference: `/v1/market/*`, `/v1/market-terminal`, `/v1/reference/instruments`, `/v1/scanner`
- Automation: `/v1/bot/start|pause|resume|stop|tick`, `/v1/bot`
- Risk/orders: `/v1/risk/*`, `/v1/orders*`, `/v1/reconcile`, `/v1/portfolio`
- Prediction markets: `/v1/prediction/*`
- CCXT / External feeds: `/v1/ccxt/*`
- Integrations/webhooks: `/v1/webhooks/tradingview`, `/v1/notifications/telegram`
- Evidence: `/v1/order-events`, `/v1/fills`, `/v1/risk/evaluations`, `/v1/account-snapshots`, `/v1/audit/*`
- Research: `/v1/backtest`, `/v1/research/*`, `/v1/signals`
- Operations: `/v1/alerts`
- Production readiness: `/v1/production/*`
- TFEX: `/v1/tfex/*`

`/openapi.json` is authoritative for the running revision.

## Documentation map

Start with [`docs/INDEX.md`](docs/INDEX.md). The repository now maintains structured documentation for requirements, architecture/design, trading domains, API/data contracts, security/privacy/supply chain, reliability/SLO/capacity, deployment/production readiness, GitHub governance, contributor workflows, and reusable evidence templates under [`docs/templates/`](docs/templates/README.md).

Key governance files:
- [`AGENTS.md`](AGENTS.md) — engineering and agent operating contract
- [`SECURITY.md`](SECURITY.md) — security model and vulnerability handling
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and validation workflow
- [`GOVERNANCE.md`](GOVERNANCE.md) — decision/approval model
- [`MAINTAINERS.md`](MAINTAINERS.md) — maintainer responsibilities
- [`SUPPORT.md`](SUPPORT.md) — support and reporting routes

GitHub-specific issue/PR forms, CODEOWNERS, Dependabot, instructions, and workflow controls live in `.github/`.

## External completion gates

Source code cannot self-certify broker/account behavior or a deployment. Remaining external gates include Settrade equity/TFEX UAT, broker/legal permissions, verified target-period exchange calendar/reference data, protected GitHub environments/rulesets where supported, production TLS/KMS/secrets, monitoring/alert delivery, backup/restore evidence, incident/rollback drills, capacity/time-sync/failover evidence, and a separately authorized minimal manual live canary.
