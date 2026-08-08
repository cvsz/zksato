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

## Instrument domains
Equity and TFEX share common interfaces but use different instrument metadata, risk, P&L, and position semantics.
