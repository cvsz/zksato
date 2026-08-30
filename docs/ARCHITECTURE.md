# zksato Architecture

## Purpose

zksato is a risk-first automated trading control plane for SET / TFEX workflows. The current implementation is a complete single-node paper/UAT application with an operator dashboard, deterministic strategies, deterministic risk checks, a paper broker, backtesting, alerts, audit history and a guarded Settrade Open API v2 equity adapter.

The central design rule is that **analysis never owns execution authority**. Every order intent passes through the same server-side risk and execution policy boundary.

## Trust boundaries

```text
Browser / API client
        |
        | HTTPS/API
        v
+----------------------------+
| FastAPI control plane      |
| - validates input          |
| - exposes dashboard        |
| - never returns secrets    |
+-------------+--------------+
              |
              v
+----------------------------+
| TradingService             |
| deterministic execution    |
| policy + live confirmation |
+-------------+--------------+
              |
        +-----+-----+
        |           |
        v           v
   RiskEngine     Broker
   deterministic   |
                  +-----------------------+
                  |                       |
                  v                       v
             PaperBroker            SettradeBroker
             local only             external API
```

No frontend flag can enable live execution. Live execution requires server configuration, complete broker credentials, deterministic risk approval and a confirmation token on the explicit manual order request. The automation engine is hard-blocked from autonomous live execution.

## Runtime data flow

```text
Quote source
    |
    v
StateStore -------> Dashboard snapshot
    |
    +----> Price history ----> StrategyEngine
    |                              |
    |                              v
    |                            Signal
    |                              |
    |                              v
    |                         AutomationEngine
    |                              |
    |                              v
    |                         OrderSubmission
    |                              |
    |                              v
    |                          RiskEngine
    |                        reject | approve
    |                           |    |
    |                           v    v
    |                         Audit TradingService
    |                                  |
    |                                  v
    |                                Broker
    |                                  |
    +<----------- orders / portfolio <-+
```

## Components

### `api.py`

Application wiring and FastAPI endpoints. It selects `PaperBroker` in paper mode and `SettradeBroker` in sandbox/live mode, then exposes market, bot, risk, order, portfolio, alerts, audit and backtest APIs.

### `dashboard.py`

Self-contained responsive operations dashboard. It provides:

- market watch
- account metrics
- portfolio and P/L
- order history
- signal history
- audit trail
- strategy and bot controls
- manual order entry
- price alerts
- paper demo-feed control
- browser-session equity chart

### `automation.py`

Coordinates deterministic strategies with risk-checked execution. It owns bot lifecycle, signal cooldown, paper protective exits, alerts and webhook notifications. It cannot bypass `TradingService`.

### `strategy.py` / `indicators.py`

Shared deterministic strategy implementation used by both automation and backtesting. Strategies include EMA/SMA crossover, RSI/Bollinger mean reversion, momentum, MACD cross, breakout, and multi-factor strategies.

### `risk.py`

Server-side pre-trade controls:

- global kill switch
- maximum daily loss
- maximum drawdown
- maximum positions
- maximum position percentage
- maximum daily order count
- maximum notional per order
- mandatory buy stop loss
- stop-loss/take-profit sanity
- available-line validation
- reference-price deviation guard
- per-trade stop-risk budget
- complete-set cost risk and directional residual limits (prediction markets)

This module has no LLM or strategy dependencies.

### `service.py`

The trusted execution boundary. It always runs risk checks and then enforces environment policy. Paper mode is local, sandbox is allowed only with broker/exchange credentials, and live mode requires explicit enablement and confirmation. Automated live calls are rejected unconditionally.

### `broker/paper.py` & `broker/ccxt.py` & `prediction/`

- `broker/paper.py`: Local deterministic fill simulator with resting limit matching, per-quote partial fill caps, quote-side price improvement, cancellation, and idempotency protection.
- `broker/ccxt.py`: Multi-exchange spot adapter (Binance, Binance TH, KuCoin, OKX, Bybit) supporting paper and sandbox execution.
- `prediction/`: Prediction market engine featuring synthetic feeds, complete-set cost calculations, `PredictionVenueAdapter` interface (`PolymarketClobAdapter`), and fail-closed `PredictionLiveGate`.

### `tradingview.py` & `notifications/telegram.py`

- `tradingview.py`: HMAC-SHA256 authenticated webhook validator supporting global and symbol-scoped secrets, alert parsing, and signal ingestion.
- `notifications/telegram.py`: Asynchronous Telegram alert and order notification dispatcher.

### `market_terminal.py`

Dark-themed TradingView charting terminal operating in read-only sandbox mode with Content-Security-Policy headers.

### `portfolio.py`

Paper cash and position accounting with weighted average price, realized P/L, unrealized P/L, mark-to-market equity, and drawdown tracking.

### `broker/settrade.py` & `tfex.py`

- `broker/settrade.py`: Optional Settrade Open API v2 equity adapter.
- `tfex.py`: Dedicated TFEX derivatives domain with contract registry, contract rollover intent generation (`generate_rollover_intents`), and dynamic margin threshold checks.

### `backtest.py`

Event-loop backtester using the same strategy engine as automation, with transaction fees, slippage modeling, and benchmark analytics.

### `persistence.py` & `store.py`

PostgreSQL durable state store using SQLAlchemy for orders, events, fills, risk evaluations, quotes, account snapshots, and outbox, alongside Redis for distributed rate-limiting and coordination.

## Execution modes

### Paper

Default. No broker credentials are required. The synthetic demo feed is available. Automated execution and protective exits are supported.

### Sandbox

Uses `SettradeBroker` and server-side credentials. Designed for Settrade UAT/simulation. Automated execution is permitted only after UAT configuration is intentionally supplied.

### Live

Uses `SettradeBroker`, but the automation engine cannot submit live orders. Explicit live order requests require:

1. `ZKSATO_TRADING_MODE=live`
2. complete Settrade credentials
3. `ZKSATO_LIVE_TRADING_ENABLED=true`
4. deterministic risk approval
5. a matching `ZKSATO_LIVE_CONFIRMATION_TOKEN`

## State and durability

The current v0.2 runtime intentionally keeps order/session state in memory. Docker Compose already provides PostgreSQL and Redis as the target production infrastructure, but durable schema, migrations, outbox processing and restart-safe reconciliation remain the highest-priority production-hardening phase.

Before mission-critical use, broker state must become the reconciliation source of truth and idempotency keys must survive process restarts.

## Failure model

Important fail-closed behavior:

- missing Settrade configuration prevents non-paper startup/execution
- live mode defaults disabled
- invalid or absent live confirmation prevents order execution
- automation cannot perform live execution
- risk rejection prevents broker invocation
- market orders in paper mode require a current quote
- duplicate paper `client_order_id` values are rejected
- demo market feed is limited to paper mode

## Future production layers

The roadmap prioritizes:

- PostgreSQL durable domain state
- Redis locks/cache
- order/deal reconciliation worker
- Settrade native realtime subscriptions and stale-feed breaker
- TFEX execution semantics and margin risk
- RBAC and authenticated operator sessions
- Vault/KMS-backed secrets
- Prometheus/OpenTelemetry/Grafana/Loki
- backup/restore and disaster recovery
- deployment-specific broker UAT certification

AI-assisted research may be added later, but it remains outside the broker mutation boundary.
