# Risk framework

Risk is independent from strategy and enforced server-side before execution.

## Current controls
Kill switch, max positions, position %, per-trade stop-risk budget, daily loss, drawdown, daily order count, max notional, available line, stop/take-profit sanity, reference-price deviation, gross/net exposure, symbol/sector limits, max open orders, session calendar, stale feed, price band, account allow-list, margin buffer, TFEX expiry/rollover restrictions.

## Portfolio-level risk
- Historical Value-at-Risk (VaR) with linear interpolation for accurate percentile estimation
- Conditional Value-at-Risk (CVaR) / Expected Shortfall
- Concentration proxy check (flags symbols exceeding portfolio ratio threshold)
- Allocation limit check
- Strategy conflict detection

## Prediction market risk
- Complete-set cost calculation (hedged sets + unhedged residual)
- Directional residual limits
- Minimum edge threshold
- Per-order USD limit

## Policy versioning
Every decision records policy version and evaluated inputs/reason codes.

## Fail-closed inputs
Missing account equity, stale/unknown reference price, unknown session state, unavailable margin where required, unresolved kill-switch state.
