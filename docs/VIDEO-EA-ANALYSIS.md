# Three-video deep analysis and EA derivation

## Scope

This document records the repository interpretation of the three supplied short trading videos and converts the visible behavior into a deterministic, bounded automation design.

The videos are treated as **behavioral evidence**, not as source code. Exact hidden EA parameters, broker contract metadata, commissions, execution rules and omitted losing sequences cannot be recovered from the recordings alone. Statements below are separated into **observed** and **inferred** behavior.

## Video inventory

| Clip | Duration | Visible platform | Instrument/timeframe | Primary evidence |
|---|---:|---|---|---|
| `20102(1)(1).mp4` | ~11.86 s | MetaTrader mobile/iOS | `XAUUSDz`, M1 | extreme accumulation of many 0.01 BUY positions during a sharp rally |
| `20109(1).mp4` | ~22.89 s | chart/TradingView-style teaching view | unspecified | PA support/demand zones, breakout/retest and explicit risk/reward examples |
| `20110(1).mp4` | ~17.21 s | MetaTrader mobile/Android | `XAUUSD.ecn`, M5 | two-sided Buy Stop / Sell Stop ladder, approximately 0.30 spacing, basket/reset behavior |

## Clip 1 — extreme position stacking during trend expansion

### Observed

The M1 chart shows `XAUUSDz` accelerating vertically from the low 4130s into the 4160-4170 area. The chart contains very dense repeated `BUY 0.01` labels across many price levels.

A trade-list frame shows approximately:

- floating result displayed near the top: `100,202.34 USD`
- balance: `76.29`
- equity: `100,278.63`
- margin: `35,873.37`
- free margin: `64,405.26`
- margin level: `279.54%`
- repeated `XAUUSDz buy 0.01` positions
- visible entry prices around `4135.593` to `4136.265`
- visible current comparison price around `4168.451`
- individual visible profits around `$32` per 0.01 position

### Inference

The combination of roughly `$100k` floating P/L, roughly `$32` per displayed 0.01 position and roughly `$35.9k` margin is consistent with **thousands of very small positions**, not a normal bounded ladder.

A rough sanity estimate using one visible position (`4168.451 - 4136.175 ≈ 32.276`) gives `100,202 / 32.276 ≈ 3,100` equivalent 0.01-position units. This is only an order-of-magnitude inference because entries vary and broker contract/margin parameters are not shown.

### Risk implication

This behavior is the most dangerous feature in the recordings. Unlimited or repeated duplicate stacking can turn a selected winning trend into catastrophic reversal/gap/margin risk. zksato therefore **does not copy this behavior literally**.

The derived system enforces:

- one virtual/pending trigger per level per cycle
- fixed quantity per level
- no martingale multiplier
- maximum total quantity
- maximum pending triggers
- basket loss boundary
- invalidation level
- cooldown after a cycle
- dedupe keys

## Clip 2 — PA zone and support/resistance flip

### Observed

The teaching chart repeatedly marks a blue horizontal area and hand-writes `PA` beside the intended entry/invalidating area.

Two visible long-position examples show:

- entry around a support/demand zone
- stop below the blue zone / PA invalidation area
- target above the entry
- displayed risk/reward examples around `1.21` and later approximately `1.88`
- a consolidation/base that breaks upward
- price later returning to the prior breakout area
- the former resistance area acting as support before another projected long move

### Inference

`PA` is interpreted as **price-action confirmation** at a structural zone. The reusable structure is:

1. identify recent swing support/resistance;
2. detect an impulsive close through the level;
3. wait for a retest within an ATR-scaled tolerance;
4. require rejection/engulfing confirmation;
5. treat the old resistance as support for a long setup, or old support as resistance for a short setup;
6. put invalidation beyond the zone instead of at an arbitrary fixed number of points.

The planner also supports a direct rejection from a recent support/demand or resistance/supply zone when a full breakout/retest sequence is not yet present, matching the first example shown in the clip.

## Clip 3 — symmetric stop-grid and basket reset

### Observed

The M5 `XAUUSD.ecn` chart shows both pending and filled orders around price.

Visible Buy Stop prices include approximately:

- `4010.21`
- `4010.51`
- `4010.81`
- `4011.11`
- `4011.41`
- `4011.71`
- `4012.01`

Visible Sell Stop prices include approximately:

- `4008.31`
- `4008.01`
- `4007.71`
- `4007.41`
- `4007.11`
- `4006.81`
- `4006.51`
- lower levels continue in the same pattern

The visible spacing is therefore approximately **0.30 price units per level**.

During the clip:

- several Buy positions are already open around `4009.01`, `4009.31`, `4009.61`, `4009.91`;
- a Sell position appears around `4008.31` after price falls through a Sell Stop;
- the trade-tab basket display changes from a small loss to positive values;
- later, order/position lines disappear while the displayed basket result remains momentarily visible;
- a fresh ladder then reappears centred around the new current price.

### Inference

The visible lifecycle is consistent with a **two-sided stop ladder / breakout grid**:

```text
anchor price
    |
    + 0.30 -> Buy Stop
    + 0.60 -> Buy Stop
    + 0.90 -> Buy Stop
    ...
    - 0.30 -> Sell Stop
    - 0.60 -> Sell Stop
    - 0.90 -> Sell Stop
    ...
```

Crossing levels opens positions in the direction of movement. A basket-level condition appears to flatten/cancel the cycle and then reseed a new ladder around the current market.

This resembles trend harvesting when price expands, but during oscillation it can accumulate opposing exposure. Combined with the massive stacking seen in clip 1, an unbounded implementation has a severe tail-risk profile.

## Derived EA architecture

The repository implementation intentionally separates **signal/planning** from **trusted execution**.

### State model

```text
IDLE
  -> detect PA zone / breakout-retest
ARMED
  -> create bounded virtual ladder
LADDER_ACTIVE
  -> quote crosses virtual trigger(s)
TRIGGERED
  -> external caller may construct a fresh OrderIntent
  -> TradingService derives trusted RiskContext
  -> RiskEngine approves/rejects
BASKET_EXIT / INVALIDATED
  -> cancel/flatten through approved execution path
COOLDOWN
  -> wait before new cycle
IDLE
```

The research planner itself stops at `TRIGGERED`; it has **no broker call** and returns `executable=false`.

## SET/Settrade adaptation

The MetaTrader videos use XAUUSD and native stop orders. zksato must not assume the same market semantics for SET equities.

For `market_profile=set_equity`:

- PA-filtered mode is the default;
- bullish evidence may produce a bounded **virtual BUY trigger ladder**;
- bearish evidence is informational/exit-oriented and does not create a naked equity short ladder;
- symmetric long/short grid mode is rejected;
- virtual triggers are crossed using trusted quote data;
- any actual order must be rebuilt server-side and pass `TradingService` + `RiskEngine`;
- market session, stale data, tick size, price band, account allow-list, exposure and operator authorization controls remain authoritative.

For TFEX/generic research, a symmetric ladder can be modeled, but it remains research/paper/UAT and does not enable TFEX production mutation.

## Safety changes versus the videos

| Video behavior | zksato derived behavior |
|---|---|
| potentially thousands of duplicate small positions | hard quantity/order caps and one trigger per level |
| fixed XAUUSD 0.30 grid | configurable absolute step or ATR-scaled step, rounded to instrument tick |
| symmetric long/short grid | disabled for SET equities; research-only elsewhere |
| hidden/unknown basket risk | explicit basket target/invalidation/max-cycle policy |
| selected winning visual examples | requires backtest/replay/walk-forward evidence before promotion |
| direct EA broker mutation | planner is non-executing; trusted execution remains separate |
| unknown recovery/martingale behavior | martingale intentionally absent |

## Default planner controls

- `grid_mode=pa_filtered`
- `market_profile=set_equity`
- `lookback_bars=48`
- `pivot_window=2`
- `ATR period=14`
- breakout buffer `0.10 ATR`
- retest tolerance `0.35 ATR`
- zone half-width `0.20 ATR`
- grid step `0.35 ATR` unless an absolute step is supplied
- 6 levels per side before caps
- fixed quantity per level
- max total quantity 12
- max pending triggers 12
- basket target metadata `1.5R`
- cycle invalidation metadata `1.0R`
- PA rejection/engulfing confirmation required

These are safe research defaults, not profitability claims.

## MQL5 reference EA

`ea/ZKSATO_VideoDerived_PA_Grid.mq5` exists to reproduce and test the MetaTrader behavior in Strategy Tester/demo.

It includes:

- PA-filtered directional grid mode;
- symmetric research grid mode;
- default absolute XAU step `0.30`;
- fixed 0.01 lot default;
- max positions/pending orders/cycle volume;
- basket profit and basket maximum-loss exits;
- spread gate;
- cooldown;
- PA rejection / engulfing confirmation;
- hard refusal to initialize on `ACCOUNT_TRADE_MODE_REAL`.

The MQL5 file is **not** the SET execution implementation.

## Required validation before any production consideration

1. Reconstruct the strategy on historical candles and verify the exact trigger lifecycle.
2. Run walk-forward and out-of-sample tests including spread, fees and slippage.
3. Test gap-through-trigger behavior and repeated quote delivery.
4. Prove trigger deduplication across restart/replay.
5. Test maximum exposure/order caps under oscillating markets.
6. Test basket-stop behavior under one-way adverse movement.
7. Test stale feed/session/price-band/tick-size failure paths.
8. Test broker reconciliation after ambiguous order outcomes.
9. Validate against Settrade UAT with the installed SDK/account.
10. Require explicit operator approval for any separately authorized live equity canary.

The three videos are useful for extracting a hypothesis. They are not evidence that the strategy is profitable, safe, or production-ready.
