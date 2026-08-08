# zksato

Risk-first automated trading platform and operations dashboard for SET / TFEX workflows.

The platform separates **market data → deterministic strategy → deterministic risk → execution → broker reconciliation → portfolio/audit**. Paper trading is the default. Settrade Open API v2 is isolated behind server-side adapters and credentials.

> **Non-negotiable execution boundary:** autonomous live-money execution is forbidden. Paper and UAT automation are supported. Live equity orders require deterministic risk approval plus a one-time, intent-bound operator approval. TFEX mutation remains UAT-only until broker certification is completed.

## v0.3 capabilities

- FastAPI control plane and responsive dashboard on port `9569`
- Paper broker with durable cash, holdings and P&L when SQL persistence is configured
- PostgreSQL/SQLAlchemy durable orders, quotes, signals, alerts, audit, idempotency and notification outbox
- Restart-safe `client_order_id` uniqueness
- Ambiguous broker outcome state and broker reconciliation worker
- Paper, Settrade UAT/sandbox and guarded live equity modes
- One-time live approval records bound to the exact order intent, with optional four-eyes enforcement
- API-key RBAC: read-only, strategy operator, order approver, risk admin, auditor and platform admin
- Rate limiting, configurable CORS/trusted hosts and browser security headers
- Settrade v2 equity adapter and realtime price/bid-offer subscription bridge
- Stale-feed, spread, open-order, notional, position, gross/symbol exposure, daily-loss and drawdown guards
- Deterministic market scanner
- EMA crossover, RSI reversion and breakout strategies
- SMA/EMA/RSI/ATR/ADX/Bollinger/VWAP indicator library
- Backtester with commission and slippage modeling
- Protective paper stop-loss/take-profit exits
- Durable webhook notification outbox
- Prometheus-compatible `/metrics`
- Dedicated TFEX domain, account/portfolio/order reads, deterministic TFEX risk checks and UAT-only mutation boundary
- PostgreSQL migration baseline under `migrations/`
- Docker Compose, PostgreSQL, Redis service baseline, non-root container, CI and governance checks
- Comprehensive `AGENTS.md`, `agents/`, `skills/`, project docs, ADRs and GitHub templates

## Architecture

```text
Market data / Settrade realtime
             |
             v
       Durable state
             |
       Strategy / Scanner
             |
             v
           Signal
             |
             v
        Risk Engine ------> reject + audit
             |
             v
      Trading Service
             |
      +------+-------+
      |              |
      v              v
 Paper Broker    Settrade Equity
      |              |
      +-------> Reconciliation
                    |
               Portfolio / audit
                    |
               Dashboard / API

Live order: Risk Admin approval -> one-time intent fingerprint -> Order Approver -> broker
TFEX: separate domain -> TFEX risk -> UAT gateway only
```

AI/LLM components may assist research and explanation but never own execution authority.

## Quick start

### Python

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
ruff check .
pytest
uvicorn zksato.api:app --reload --port 9569
```

Open:

- Dashboard: `http://127.0.0.1:9569/`
- OpenAPI: `http://127.0.0.1:9569/docs`
- Health: `http://127.0.0.1:9569/health`

### Docker Compose

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD before any non-local deployment.
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:9569/health
```

Compose automatically wires the API to PostgreSQL. Redis is present as the coordination target but is not a correctness dependency yet.

## Authentication

Trusted local development defaults to `ZKSATO_AUTH_REQUIRED=false`. Before exposing the service, enable RBAC and use separate high-entropy keys:

```dotenv
ZKSATO_AUTH_REQUIRED=true
ZKSATO_API_KEYS=risk-random-key:risk_admin;order-random-key:order_approver;reader-key:read_only
```

Clients may send `X-API-Key` or `Authorization: Bearer ...`. Never put these values in frontend source, logs or version control.

## Live equity approval flow

Live mode remains disabled by default. When operational prerequisites are met:

```dotenv
ZKSATO_TRADING_MODE=live
ZKSATO_LIVE_TRADING_ENABLED=true
ZKSATO_LIVE_REQUIRES_CONFIRMATION=true
ZKSATO_REQUIRE_DISTINCT_APPROVER=true
ZKSATO_LEGACY_LIVE_TOKEN_ENABLED=false
```

1. A `risk_admin` submits the exact proposed `OrderIntent` to `POST /v1/live-approvals`.
2. The server stores a short-lived fingerprint of that exact intent.
3. A distinct `order_approver` sends `POST /v1/orders` with `X-Live-Approval-Id`.
4. The server re-runs deterministic risk checks, consumes the approval once and only then reaches the broker adapter.
5. Ambiguous broker outcomes become `needs_reconciliation`; the system never blindly retries them.

Autonomous live trading is still rejected even when live mode is enabled.

## Settrade UAT

Install the official SDK dependency:

```bash
pip install -e '.[settrade]'
```

Configure server-side credentials and the Settrade SDK for its simulated/UAT environment before any broker mutation. Example application variables:

```dotenv
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=...
ZKSATO_SETTRADE_APP_SECRET=...
ZKSATO_SETTRADE_BROKER_ID=...
ZKSATO_SETTRADE_APP_CODE=ALGO_EQ
ZKSATO_SETTRADE_ACCOUNT_NO=...
ZKSATO_SETTRADE_DERIVATIVES_ACCOUNT_NO=...
ZKSATO_SETTRADE_PIN=...
```

Use `/v1/market/settrade/start` to start configured realtime subscriptions. Equity sandbox automation may run through the normal risk/service boundary. TFEX reads and `/v1/tfex/orders/uat` are isolated behind the dedicated TFEX domain.

## API groups

- Platform/auth: `/health`, `/metrics`, `/v1/config`, `/v1/auth/me`, `/v1/dashboard`
- Market: `/v1/market/*`, `/v1/scanner`
- Automation: `/v1/bot/*`
- Risk/execution: `/v1/risk/check`, `/v1/orders`, `/v1/reconcile`, `/v1/portfolio`
- Approval: `/v1/live-approvals`
- Research: `/v1/backtest`, `/v1/signals`
- Operations: `/v1/alerts`, `/v1/audit`
- TFEX: `/v1/tfex/account`, `/v1/tfex/portfolio`, `/v1/tfex/orders`, `/v1/tfex/risk/check`, `/v1/tfex/orders/uat`

The authoritative schema is always available from `/docs` and `/openapi.json` for the deployed revision.

## Risk defaults

```dotenv
ZKSATO_KILL_SWITCH=false
ZKSATO_MARKET_DATA_STALE_SECONDS=10
ZKSATO_MAX_POSITIONS=5
ZKSATO_MAX_POSITION_PCT=10
ZKSATO_MAX_RISK_PER_TRADE_PCT=0.5
ZKSATO_MAX_DAILY_LOSS_PCT=2
ZKSATO_MAX_DRAWDOWN_PCT=5
ZKSATO_MAX_ORDERS_PER_DAY=50
ZKSATO_MAX_OPEN_ORDERS=20
ZKSATO_MAX_NOTIONAL_PER_ORDER=100000
ZKSATO_MAX_GROSS_EXPOSURE_PCT=80
ZKSATO_MAX_SYMBOL_EXPOSURE_PCT=20
ZKSATO_MAX_SPREAD_PCT=3
ZKSATO_MAX_TFEX_CONTRACTS=20
ZKSATO_MAX_TFEX_MARGIN_USAGE_PCT=50
ZKSATO_REQUIRE_STOP_LOSS=true
```

Risk limits are server-side and cannot be disabled by browser state.

## Repository map

```text
src/zksato/
  api.py              HTTP API/application wiring
  approvals.py        one-time live intent approvals
  auth.py             authentication/RBAC
  automation.py       strategy automation/protective exits
  backtest.py         cost-aware strategy backtesting
  config.py           environment and safety policy
  dashboard.py        embedded operations dashboard
  domain.py           typed domain contracts
  indicators.py       technical indicators
  market.py           synthetic paper feed
  market_settrade.py  Settrade realtime bridge
  notifications.py    durable outbox dispatcher
  observability.py    Prometheus metrics
  persistence.py      SQL durable state
  portfolio.py        paper accounting/recovery
  reconcile.py        broker-state convergence
  risk.py             equity risk engine
  scanner.py          deterministic market scanner
  security.py         HTTP hardening
  service.py          trusted execution boundary
  store.py            state-store contract/in-memory adapter
  strategy.py         deterministic strategies
  tfex.py             isolated TFEX domain/UAT gateway
  broker/
    base.py
    paper.py
    settrade.py
migrations/
tests/
docs/
agents/
skills/
```

## Engineering workflow

Read `AGENTS.md` and `docs/INDEX.md` before substantive changes. Capability status is tracked in `docs/FEATURE-MATRIX.md`; remaining deployment and broker-certification gates are tracked in `ROADMAP.md` and `docs/EXECUTION-PLAN.md`.

## What still requires external evidence

The codebase can implement guards and adapters, but it cannot self-certify broker or infrastructure behavior. Before production use you still need actual Settrade UAT evidence for the installed SDK/account, broker permissions, managed TLS/secrets, database backup/restore drills, production monitoring/alerts, and a manual-confirmation canary. TFEX live mutation remains intentionally unavailable until its UAT lifecycle and margin semantics are certified.
