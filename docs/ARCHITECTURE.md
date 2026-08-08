# zksato Architecture

## Principles

1. **Risk before execution.** Every order intent passes deterministic server-side policy before it can reach a broker adapter.
2. **No browser-held broker secrets.** Credentials belong only in the backend runtime/secret store.
3. **No silent mode fallback.** Sandbox/live mode must never quietly route to the paper adapter.
4. **Idempotent execution.** Every mutating order request should carry a stable client order ID and be reconciled against broker state.
5. **AI is advisory.** LLM/agent components may rank, summarize, explain or propose signals; they do not bypass the risk engine or execution policy.
6. **Paper -> Sandbox -> Live.** Promotion between environments is explicit and auditable.

## Logical architecture

```text
                       +----------------------+
                       |  Dashboard / Client  |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       | FastAPI Control Plane|
                       +----------+-----------+
                                  |
               +------------------+------------------+
               |                                     |
               v                                     v
      +------------------+                   +------------------+
      | Market / Scanner |                   | Portfolio / P&L  |
      +--------+---------+                   +------------------+
               |
               v
      +------------------+
      | Strategy Engine  |
      +--------+---------+
               |
               v
      +------------------+
      |  Order Intent    |
      +--------+---------+
               |
               v
      +------------------+
      | Deterministic    |
      | Risk Engine      |
      +---+----------+---+
          |          |
       reject      approve
          |          |
          v          v
       Audit   +------------------+
               | Execution Service|
               +---------+--------+
                         |
            +------------+-------------+
            |            |             |
            v            v             v
         Paper       Settrade UAT   Settrade Prod
         Broker       / Sandbox       (opt-in)
```

## Current Phase 0 modules

### `domain.py`
Defines validated order intent, risk context, risk decisions and order records. Validation is performed before the application service receives an intent.

### `risk.py`
Contains deterministic rules for:

- daily loss circuit breaker
- portfolio drawdown circuit breaker
- maximum number of positions
- maximum position allocation
- required stop loss for buy orders
- stop-loss sanity check
- available-line/notional validation when line data is supplied

### `broker/base.py`
Defines the broker port used by application services. Provider-specific SDK calls must remain behind this boundary.

### `broker/paper.py`
Safe in-memory broker. It records accepted orders and rejects duplicate `client_order_id` values. It never contacts Settrade.

### `service.py`
Orchestrates risk and execution. It refuses to use the paper broker when the requested mode is `sandbox` or `live`, preventing accidental mode confusion.

### `api.py`
Provides a minimal API on port 9999 by convention. It exposes only non-secret policy values from configuration.

## Target components

### Market data service

Responsibilities:

- Settrade quote/realtime subscriptions
- symbol normalization
- timestamp and sequence validation
- stale-feed detection
- bounded in-memory cache
- persistence of bars/ticks where licensed and appropriate

### Scanner service

Initial scanners:

- price/volume breakout
- relative volume
- momentum ranking
- EMA/SMA trend filters
- RSI/ATR/ADX filters
- SET50/SET100 configurable universes
- TFEX contract watchlists

### Strategy service

Strategies generate **signals**, not broker orders. A signal contains instrument, direction, entry thesis, invalidation/stop, optional target and expiry. Position sizing is done by deterministic policy.

### Risk service

Target controls beyond Phase 0:

- risk-per-trade sizing
- gross/net exposure limits
- per-symbol and sector limits
- concentration rules
- market-session gate
- stale-price protection
- slippage/price-band guard
- duplicate order fingerprinting
- kill switch
- consecutive-error circuit breaker
- account and broker allow-list
- manual approval mode

### Execution service

Target behavior:

1. validate current account state
2. obtain fresh quote/order-book state
3. generate an idempotency key
4. submit through the configured adapter
5. persist broker order ID
6. reconcile status until terminal state
7. handle cancel/change safely
8. emit audit events for every transition

### Persistence

Planned stack:

- PostgreSQL for orders, signals, positions, audit and configuration metadata
- Redis for short-lived locks, rate limiting and cache
- optional TimescaleDB extension for time-series analytics

The in-memory Phase 0 broker is intentionally not durable.

## Settrade adapter boundary

The official Settrade Open API Python SDK is integrated only inside a provider adapter. The adapter must support separate UAT/Sandbox and production configuration and map provider responses into zksato domain models.

No Settrade `app_secret`, PIN or equivalent credential may be returned by API endpoints, written to logs, embedded in the dashboard bundle or committed to Git.

## AI boundary

Allowed AI tasks:

- summarize market context/news supplied by approved data sources
- explain deterministic scanner output
- rank already-generated candidates
- propose strategy hypotheses for backtesting
- generate daily reports and anomaly summaries

Disallowed architecture:

```text
LLM -> unrestricted place_order()
```

Required architecture:

```text
LLM/Strategy proposal
        |
        v
validated signal
        |
        v
deterministic sizing + risk
        |
        v
execution policy
        |
        v
broker adapter
```

## Deployment target

Phase 1 deployment uses Docker Compose:

```text
api       FastAPI
postgres  durable state
redis     coordination/cache
worker    scanner/strategy/order reconciliation
```

Production should add TLS termination, secret management, metrics, centralized logs, backups and network restrictions.

## Promotion checklist for live execution

Live trading stays disabled until all of the following are true:

- Sandbox adapter integration tests pass
- order place/cancel/change/reconcile tests pass
- broker/account identifiers are allow-listed
- credentials are supplied by a secret store
- duplicate-order protection is durable
- market-data stale checks are enabled
- daily-loss and drawdown circuit breakers are tested
- kill switch is operational
- monitoring and alerts are operational
- operator explicitly enables live mode server-side
- broker/Settrade requirements and permissions have been confirmed
