# Risk framework

Risk is independent from strategy and enforced server-side before execution.

## Current controls
Kill switch, max positions, position %, per-trade stop-risk budget, daily loss, drawdown, daily order count, max notional, available line, stop/take-profit sanity, reference-price deviation, gross/net exposure, symbol/sector limits, max open orders, session calendar, stale feed, price band, account allow-list, margin buffer, TFEX expiry/rollover restrictions.

## Protections (advisory layer, evaluated before RiskEngine)

| Protection | Description |
|------------|-------------|
| CooldownPeriod | Prevents trading for a period after a trade exit |
| StoplossGuard | Pauses trading after consecutive losses within a lookback window |
| DrawdownProtection | Pauses trading when daily drawdown exceeds threshold |
| VolatilityProtection | Pauses trading when recent price volatility exceeds threshold |
| TimeBasedProtection | Pauses trading during configured hours (e.g., lunch break) |
| ConsecutiveLossProtection | Pauses trading after N consecutive losses |

All protections are advisory — they can veto trades but never bypass RiskEngine.

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

## Agent Rate Limiting
Per-agent rate limiting (default 120 requests/minute) enforced at the API layer for agent session management and authenticated agent operations. Supports in-memory tracking with optional Redis coordination.
