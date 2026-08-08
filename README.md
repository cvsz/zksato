# zksato

Risk-first automated trading platform and operations dashboard for SET / TFEX workflows.

The platform separates **market data → deterministic strategy → deterministic risk → execution → portfolio/audit**. Paper trading is the default. Settrade Open API v2 is available behind an explicit adapter and server-side credentials.

> **Execution boundary:** autonomous live trading is intentionally blocked. Automation can run in paper mode and Settrade UAT/sandbox. In live mode the bot can generate signals, while each real order requires explicit server-authorized confirmation.

## What is implemented

- FastAPI control plane on port `9999`
- Responsive dark trading dashboard at `/`
- Paper broker with immediate market/marketable-limit fill simulation
- Cash, holdings, realized/unrealized P&L and mark-to-market portfolio
- Market quote ingestion API and synthetic demo feed
- Shared price-history store
- Strategies: EMA crossover, RSI mean reversion, breakout
- Bot start/stop/tick lifecycle
- Automated paper/UAT execution
- Protective stop-loss and take-profit exits in paper mode
- Deterministic pre-trade risk engine
- Global kill-switch policy
- Position-count, allocation, per-trade risk, daily-loss, drawdown, order-count, notional and price-deviation controls
- Duplicate client-order protection
- Price alerts
- Generic webhook notifications
- Backtesting engine using the same strategy implementation as automation
- Order, signal and audit history APIs
- Settrade Open API v2 equity adapter with lazy optional SDK loading
- Explicit paper / sandbox / live modes
- Live confirmation-token boundary
- Docker image, Docker Compose stack, health check, non-root container
- Ruff + pytest GitHub Actions CI

## Architecture

```text
                  Quote / Settrade data
                          |
                          v
                    State / History
                          |
                  +-------+--------+
                  |                |
                  v                v
             Alert Engine     Strategy Engine
                                   |
                                   v
                                 Signal
                                   |
                                   v
                             Risk Engine
                          reject /     \ approve
                               /       \
                              v         v
                           Audit    Execution Service
                                      |
                         +------------+------------+
                         |                         |
                         v                         v
                    Paper Broker             Settrade v2
                         |                  UAT / confirmed live
                         v
                 Portfolio / P&L
                         |
                         v
                    Dashboard/API
```

AI or LLM components may later assist with research, explanation and ranking, but are not permitted to bypass deterministic risk or the live confirmation boundary.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
pytest
uvicorn zksato.api:app --reload --port 9999
```

Open:

- Dashboard: `http://127.0.0.1:9999/`
- OpenAPI docs: `http://127.0.0.1:9999/docs`
- Health: `http://127.0.0.1:9999/health`

### Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Then open `http://127.0.0.1:9999/`.

## Dashboard controls

The dashboard includes market watch, portfolio/P&L, order history, bot controls, strategy selection, manual orders, alerts, signals, audit trail and an equity monitor.

For a zero-credential local demonstration, press **Start demo feed**. Synthetic prices are clearly isolated to paper mode and never represent actual SET prices.

## API surface

### Platform

- `GET /health`
- `GET /v1/config`
- `GET /v1/dashboard`

### Market data

- `POST /v1/market/quote`
- `GET /v1/market/quotes`
- `GET /v1/market/history/{symbol}`
- `POST /v1/market/demo/start`
- `POST /v1/market/demo/stop`

### Automation

- `POST /v1/bot/start`
- `POST /v1/bot/stop`
- `POST /v1/bot/tick`
- `GET /v1/bot`

### Risk and execution

- `POST /v1/risk/check`
- `POST /v1/orders`
- `GET /v1/orders`
- `DELETE /v1/orders/{order_id}`
- `GET /v1/portfolio`

### Research / operations

- `POST /v1/backtest`
- `GET /v1/signals`
- `POST /v1/alerts`
- `GET /v1/alerts`
- `DELETE /v1/alerts/{alert_id}`
- `GET /v1/audit`

## Settrade Open API v2

Install the optional adapter dependency:

```bash
pip install -e '.[settrade]'
```

Set server-side values in `.env`:

```dotenv
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=...
ZKSATO_SETTRADE_APP_SECRET=...
ZKSATO_SETTRADE_BROKER_ID=...
ZKSATO_SETTRADE_APP_CODE=ALGO_EQ
ZKSATO_SETTRADE_ACCOUNT_NO=...
ZKSATO_SETTRADE_PIN=...
```

The official SDK also uses `settradesdkv2_config.txt`; use `environment=uat` for its simulated environment and `environment=prod` only when intentionally operating production.

### Live mode

Live mode requires all of the following server-side controls:

```dotenv
ZKSATO_TRADING_MODE=live
ZKSATO_LIVE_TRADING_ENABLED=true
ZKSATO_LIVE_REQUIRES_CONFIRMATION=true
ZKSATO_LIVE_CONFIRMATION_TOKEN=<long-random-secret>
```

The automation engine still refuses autonomous live execution. Live orders are accepted only through the explicit order endpoint with the matching confirmation token and after deterministic risk checks.

## Risk policy

Important defaults are intentionally conservative and configurable from environment variables:

```dotenv
ZKSATO_KILL_SWITCH=false
ZKSATO_MAX_POSITIONS=5
ZKSATO_MAX_POSITION_PCT=10
ZKSATO_MAX_RISK_PER_TRADE_PCT=0.5
ZKSATO_MAX_DAILY_LOSS_PCT=2
ZKSATO_MAX_DRAWDOWN_PCT=5
ZKSATO_MAX_ORDERS_PER_DAY=50
ZKSATO_MAX_NOTIONAL_PER_ORDER=100000
ZKSATO_REQUIRE_STOP_LOSS=true
```

All controls execute server-side. Frontend state cannot disable them.

## Repository map

```text
src/zksato/
  api.py               HTTP API + application wiring
  automation.py        bot, protective exits, alerts, notifications
  backtest.py          strategy backtesting
  config.py            environment and safety policy
  dashboard.py         embedded operations dashboard
  domain.py            typed domain models
  indicators.py        technical indicators
  market.py            synthetic paper feed
  portfolio.py         paper accounting
  risk.py              deterministic risk engine
  service.py           execution-policy boundary
  store.py             process-local state adapter
  strategy.py          EMA / RSI / breakout strategies
  broker/
    base.py             broker protocol
    paper.py            paper execution
    settrade.py         Settrade Open API v2 adapter

tests/
docs/
ROADMAP.md
```

## Production hardening still recommended

The current release is a complete single-node paper/UAT platform. Before running mission-critical production workloads, replace process-local state with PostgreSQL/Redis persistence, add authenticated RBAC, durable event/outbox processing, broker-order reconciliation workers, metrics/tracing, encrypted secret management, disaster recovery and an independent UAT certification checklist. Those items remain tracked in `ROADMAP.md` because they require deployment-specific infrastructure rather than only application code.
