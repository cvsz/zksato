# zksato

Risk-first automation, research, and operations control plane for SET / TFEX workflows.

zksato separates **market data → deterministic strategy/research → deterministic risk → controlled execution → reconciliation → portfolio/audit**. Paper mode is the default. Settrade Open API v2 lives behind server-side adapters and credentials.

> **Permanent boundary:** autonomous live-money execution is forbidden. Paper/UAT automation is supported; production-facing actions remain behind deterministic risk, explicit operator controls, reconciliation, and external readiness evidence. TFEX mutation remains UAT-only.

## v0.4 — P0-P6 source completion

The repository-controlled completion plan is implemented across durable correctness, trusted market/risk, security/operator controls, TFEX isolation, observability/recovery, strategy research, and production-readiness gates.

Key capabilities:

- FastAPI control plane and responsive dashboard on port `9569`
- PostgreSQL durable state for orders, order events, fills, risk evaluations, account snapshots, quotes, OHLCV bars, signals, alerts, audit, idempotency, runtime state, and notification outbox
- versioned migrations under `migrations/`
- restart-safe `client_order_id` uniqueness
- persistent paper cash/holdings/P&L
- ambiguous broker-outcome classification without blind retry
- convergence-aware broker reconciliation and independent session fill/position reconciliation
- optional Redis distributed coordination and distributed rate-limit state
- supervised Settrade realtime price/bid-offer subscriptions with reconnect/backoff, freshness, gap, and out-of-order diagnostics
- trusted instrument metadata for sector, tick-size, price-band, and session controls
- deterministic risk covering stale data, spread, open orders, position sizing, notional, daily loss, drawdown, gross/net/symbol/sector exposure, account allow-list, tick, and price-band checks
- deterministic scanner plus EMA/RSI/breakout strategies and SMA/EMA/RSI/ATR/ADX/Bollinger/VWAP indicators
- durable historical replay, commission/slippage-aware backtesting, session-aware walk-forward/OOS research, strategy/version registry, drift primitive, and promotion evidence gates
- API-key RBAC plus HMAC-signed expiring HttpOnly sessions and CSRF protection
- CORS, trusted hosts, CSP/HSTS, security headers, secret-file loading, sensitive-data redaction, and hash-linked audit events
- one-time intent-bound privileged approvals with optional four-eyes separation
- Prometheus metrics, JSON correlation logs, optional OpenTelemetry traces, alert/SLO configuration, load probe, PostgreSQL backup/restore scripts, and DR runbook
- dedicated TFEX domain with contract metadata, LONG/SHORT, OPEN/CLOSE/AUTO, margin/contract/tick/expiry controls, settlement helper, read APIs, and UAT-only mutation gateway
- machine-readable production-readiness and non-executing canary-planning controls
- UAT, secrets, SLO, DR, and production-readiness runbooks
- CI with PostgreSQL + Redis services, compile, all migrations, dependency consistency, Ruff, pytest, and Compose validation
- repository engineering system: `AGENTS.md`, specialist `agents/`, reusable `skills/`, ADRs, governance, and project documentation

## Architecture

```text
Settrade / paper market data
            |
            v
   durable quotes + bars
            |
      +-----+------+----------------+
      |            |                |
      v            v                v
   Scanner      Strategy         Research
                   |        replay / backtest / OOS
                   v                |
                 Signal <-----------+
                   |
                   v
         trusted Risk Context
                   |
                   v
             Risk Engine ------> reject + audit
                   |
                   v
            Trading Service
                   |
           +-------+--------+
           |                |
           v                v
      Paper Broker      Settrade Equity
           |                |
           +-------> Reconciliation
                          |
                    fills / portfolio
                          |
                 audit / metrics / API

TFEX: separate domain -> contract reference -> TFEX risk -> UAT gateway only
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
pytest -m "not uat and not performance"
uvicorn zksato.api:app --reload --port 9569
```

Open:

- Dashboard: `http://127.0.0.1:9569/`
- OpenAPI: `http://127.0.0.1:9569/docs`
- Health: `http://127.0.0.1:9569/health`

### Docker Compose

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD before non-local deployment.
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:9569/health
```

Compose wires the API to PostgreSQL and Redis. PostgreSQL remains the durable correctness boundary; Redis is used for coordination and distributed abuse protection.

## Authentication and sessions

Trusted local development defaults to `ZKSATO_AUTH_REQUIRED=false`. For an exposed environment, configure role-separated credentials and a session-signing secret:

```dotenv
ZKSATO_AUTH_REQUIRED=true
ZKSATO_API_KEYS=risk-random-key:risk_admin;order-random-key:order_approver;reader-key:read_only
ZKSATO_SESSION_SECRET=replace-with-a-long-random-secret
ZKSATO_CSRF_REQUIRED=true
```

Machine clients can use `X-API-Key` or Bearer authentication. `POST /v1/auth/session` exchanges a valid machine credential for a signed, expiring HttpOnly session and a CSRF token. Supported secrets can also be mounted under `ZKSATO_SECRET_DIR`; see `docs/SECRETS-RUNBOOK.md`.

## Settrade UAT

Install the official optional SDK dependency:

```bash
pip install -e '.[settrade]'
```

Set application credentials only on the server and configure the SDK for the authorized UAT/simulated environment before broker-facing validation. The realtime supervisor is controlled through `/v1/market/settrade/start`, `/stop`, and `/status`. The UAT evidence checklist and non-mutating probe are documented in `docs/UAT-CERTIFICATION.md`.

Actual broker/account behavior cannot be certified by repository code alone.

## Trusted reference data

Optional strict reference controls can validate instrument tick size, price bands, sector concentration, market sessions, TFEX multiplier/tick/expiry metadata, and account allow-lists. Representative settings are documented in `.env.example`.

For UAT/production-like validation, use trusted reference data and enable strict/session enforcement only after the supplied metadata and session calendar are verified for the target market/account.

## Research pipeline

The research boundary has no broker submission authority. It supports:

```text
historical bars
    ↓
deterministic replay
    ↓
fee/slippage backtest
    ↓
walk-forward / out-of-sample
    ↓
durable strategy/version/run evidence
    ↓
research → paper → UAT → manual-production-readiness evidence gate
```

Strategy performance is empirical evidence, not a source-code guarantee.

## API groups

- Platform/auth: `/health`, `/metrics`, `/v1/config`, `/v1/auth/*`, `/v1/dashboard`
- Market/reference: `/v1/market/*`, `/v1/reference/instruments`, `/v1/scanner`
- Automation: `/v1/bot/*`
- Risk/control: `/v1/risk/*`, `/v1/orders`, `/v1/reconcile`, `/v1/portfolio`
- Evidence/audit: `/v1/order-events`, `/v1/fills`, `/v1/risk/evaluations`, `/v1/audit/*`
- Research: `/v1/backtest`, `/v1/research/*`, `/v1/signals`
- Operations: `/v1/alerts`
- Production readiness: `/v1/production/*`
- TFEX: `/v1/tfex/*`

The deployed `/docs` and `/openapi.json` are authoritative for the running revision.

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
ZKSATO_MAX_NET_EXPOSURE_PCT=80
ZKSATO_MAX_SYMBOL_EXPOSURE_PCT=20
ZKSATO_MAX_SECTOR_EXPOSURE_PCT=35
ZKSATO_MAX_SPREAD_PCT=3
ZKSATO_MAX_TFEX_CONTRACTS=20
ZKSATO_MAX_TFEX_MARGIN_USAGE_PCT=50
ZKSATO_REQUIRE_STOP_LOSS=true
```

Risk limits execute server-side; browser state cannot disable them.

## Operations

Useful production-readiness material:

- `docs/EXECUTION-PLAN.md` — P0-P6 completion status and evidence boundaries
- `docs/FEATURE-MATRIX.md` — capability truth table
- `docs/UAT-CERTIFICATION.md` — Settrade UAT evidence checklist
- `docs/PRODUCTION-READINESS.md` — runtime/external readiness model
- `docs/SLO.md` — service objectives and failure actions
- `docs/DR-RUNBOOK.md` — backup/restore and recovery sequence
- `docs/SECRETS-RUNBOOK.md` — secret handling and rotation
- `deploy/monitoring/` — Prometheus alerts and OTel collector baseline
- `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh`, `scripts/load_test.py`, `scripts/uat_certify.py`

## Repository map

```text
src/zksato/
  api.py                 HTTP API/application wiring
  approvals.py           intent-bound approval records
  auth.py                API-key RBAC and signed sessions
  automation.py          paper/UAT strategy automation
  backtest.py            fee/slippage backtesting
  config.py              environment and safety policy
  coordination.py        Redis/local coordination
  dashboard.py           embedded operations dashboard
  domain.py              typed durable contracts
  indicators.py          technical indicators
  market.py              synthetic paper feed
  market_rules.py        session/instrument reference policy
  market_settrade.py     supervised Settrade realtime bridge
  notifications.py       durable outbox dispatcher
  observability.py       metrics/logging/tracing
  persistence.py         PostgreSQL durable state
  portfolio.py           paper accounting/recovery
  production.py          readiness/canary evidence gates
  reconcile.py           broker order/fill convergence
  research.py            replay/OOS/version/promotion pipeline
  risk.py                deterministic equity risk engine
  scanner.py             deterministic market scanner
  security.py            HTTP hardening/redaction
  service.py             trusted execution boundary
  session_reconcile.py   durable-fill vs broker-position comparison
  store.py               state-store contract/in-memory adapter
  strategy.py            deterministic strategies
  tfex.py                isolated TFEX domain/UAT gateway
  broker/
migrations/
deploy/
scripts/
tests/
docs/
agents/
skills/
```

## External completion evidence

Repository code cannot self-certify a broker account or deployment. Production readiness still depends on actual Settrade UAT evidence, broker/organizational approval, trusted reference data, TLS and managed-secret deployment, recovery/capacity/alert drills, and explicit operator authorization. Those requirements are represented as fail-closed evidence gates rather than being marked complete without proof.
