# zksato

Production-oriented automated trading platform scaffold for SET / TFEX workflows, designed around a strict separation between market analysis, deterministic risk controls, and broker execution.

> **Safety default:** live order execution is disabled. The repository starts with a paper broker and a risk engine. A real Settrade adapter must be configured explicitly and should be validated against Settrade Sandbox before production use.

## Goals

- Market scanner and strategy signals
- Deterministic pre-trade risk engine
- Paper / sandbox / live execution modes
- Order idempotency and reconciliation boundary
- Portfolio and P&L services
- FastAPI control plane
- Audit-friendly decision records
- Notification and dashboard integration points
- SET and TFEX provider abstraction
- AI-assisted analysis without granting an LLM unrestricted order placement

## Architecture

```text
Market Data
    |
    v
Scanner / Strategy
    |
    v
Signal
    |
    v
Risk Engine -----> Reject + audit
    |
    v
Execution Service
    |
    +---- Paper Broker (default)
    +---- Settrade Sandbox Adapter (next)
    +---- Settrade Production Adapter (explicit opt-in)
    |
    v
Orders / Portfolio / P&L / Alerts
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
pytest
uvicorn zksato.api:app --reload --port 9999
```

Open `http://127.0.0.1:9999/docs` for the API documentation.

## Current API

- `GET /health`
- `GET /v1/config`
- `POST /v1/risk/check`
- `POST /v1/orders` — paper execution only in the initial scaffold
- `GET /v1/orders`

## Live trading policy

`TRADING_MODE=paper` is the repository default. Live execution must never be enabled only by changing frontend state. The server-side execution adapter, credentials, account allow-list, risk policy and environment must all agree before any real order is accepted.

For Settrade integration, use the official `settrade-v2` SDK and validate the adapter in the Settrade Sandbox/UAT environment before switching to production.

## Repository map

```text
src/zksato/
  api.py             FastAPI control plane
  config.py          environment/settings
  domain.py          order and risk domain models
  risk.py            deterministic risk policy
  service.py         application orchestration
  broker/
    base.py           broker execution contract
    paper.py          safe default execution adapter

tests/                unit tests
docs/ARCHITECTURE.md  detailed system design
ROADMAP.md             implementation plan
```

## Status

Phase 0 scaffold is implemented. Next priority is the Settrade Sandbox adapter, market-data ingestion, persistence, order reconciliation, and strategy/backtest services.
