# TFEX domain plan

TFEX is a dedicated derivatives domain, not an equity flag.

## Required model
Contract root/series, expiry, multiplier, tick size/value, trading session, long/short, open/close/auto-position, margin, settlement, rollover state.

## Required services
Contract universe refresh, margin/account adapter, TFEX order adapter, position/P&L accounting, expiry/rollover scheduler, TFEX risk policy, reconciliation.

## Risk
Max contracts, notional/delta proxy as appropriate, initial/maintenance margin buffer, daily loss/drawdown, concentration by underlying, expiry proximity, stale price, session/price-band rules.

## Promotion
Unit/state-machine tests → paper derivatives simulator → Settrade UAT open/close long/short and margin scenarios → controlled operator-only live canary.
