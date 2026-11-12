# Domain model

## Core aggregates
### OrderIntent
Immutable requested action: account, market, symbol/contract, side, quantity, order type, price, validity, source, client idempotency key.

### RiskDecision
Decision tied to an exact intent and policy version, with approved/rejected status, reason codes, evaluated inputs, and timestamp.

### Order
Local lifecycle record mapping client order ID to broker order ID. States should include pending-submit, accepted/open, partially-filled, filled, cancel-pending, cancelled, rejected, unknown/needs-reconciliation.

### Fill/Deal
Broker-confirmed execution event with quantity, price, fee metadata, broker IDs, timestamp, and deduplication key.

### Position
Quantity, average cost, market mark, realized/unrealized P&L, exposure, instrument metadata.

### Signal
Deterministic strategy output with strategy version, symbol, action, price/reference data, confidence/metadata, created/expiry timestamps.

### StrategyRun
Configuration/version/data window and produced signals/orders.

### AuditEvent
Append-oriented actor/action/resource/outcome/correlation metadata with redaction rules.

### ApiKey
API key metadata (raw value never stored — SHA-256 hash only). Fields: key_id, role, description, created_at, expires_at, is_active, last_used_at, usage_count.

### AgentSession
Agent session metadata: agent_id, created_at, expires_at, ttl_seconds, is_active.

## Instrument domains
Equity and TFEX share common interfaces but use different instrument metadata, risk, P&L, and position semantics.

## Strategy Framework (Freqtrade-compatible)

### IStrategy
Abstract interface with `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()`, `signal_to_intent()`.

### Strategies (16 total)
- `ema_cross`, `rsi_reversion`, `macd_cross`, `bollinger_reversion`, `stochastic_oscillator`, `williams_r`, `atr_channel`
- `momentum`, `breakout`, `scalp`, `swing`, `position`, `vwap`, `llm_sentiment`, `multi_factor`, `tfex_spread`

All strategies are advisory-only; signals route through RiskEngine before any order submission.

## Protections (6 total)
- `CooldownPeriodProtection` — prevents trading after a trade exit
- `StoplossGuardProtection` — pauses trading after consecutive losses
- `DrawdownProtection` — pauses trading when daily drawdown exceeds threshold
- `VolatilityProtection` — pauses trading when recent price volatility exceeds threshold
- `TimeBasedProtection` — pauses trading during configured hours
- `ConsecutiveLossProtection` — pauses trading after N consecutive losses

## Pairlists (6 total)
- `StaticPairList` — whitelist/blacklist
- `VolumePairList` — dynamic by 24h volume ranking
- `ChangePctPairList` — dynamic by 24h price change percentage
- `MomentumPairList` — dynamic by recent price momentum
- `VolatilityPairList` — filtered by volatility threshold
- `SectorDiversifiedPairList` — limits exposure per sector

## Agent Session Management
Session lifecycle: create → validate → expire. Sessions are stored with TTL for automatic cleanup and support per-agent rate limiting.
