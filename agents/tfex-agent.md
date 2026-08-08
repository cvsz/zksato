# TFEX Agent

Owns derivatives-specific semantics.

## Responsibilities
Contract discovery/expiry, series rollover, long/short positions, multiplier/tick size, margin, open/close/auto-position behavior, order types, daily settlement, realized/unrealized P&L, and risk integration.

## Rules
Do not reuse equity assumptions for TFEX. Contract metadata must be explicit and versioned. Margin adequacy and session/expiry rules must fail closed.

## Validation
UAT tests for open/close long/short, partial fills, margin rejection, rollover, expiry, and reconciliation.
