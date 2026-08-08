# Risk framework

Risk is independent from strategy and enforced server-side before execution.

## Current controls
Kill switch, max positions, position %, per-trade stop-risk budget, daily loss, drawdown, daily order count, max notional, available line, stop/take-profit sanity, reference-price deviation.

## Target controls
Gross/net exposure, symbol/sector limits, max open orders, order-rate limits, session calendar, stale feed, price band/slippage, consecutive broker errors, account allow-list, margin buffer, TFEX expiry/rollover restrictions.

## Policy versioning
Every decision should record policy version and evaluated inputs/reason codes.

## Fail-closed inputs
Missing account equity, stale/unknown reference price, unknown session state, unavailable margin where required, unresolved kill-switch state.
