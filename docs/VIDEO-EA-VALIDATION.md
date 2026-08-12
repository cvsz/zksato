# Video-derived EA validation protocol

The video-derived strategy is a hypothesis reconstructed from visual evidence. It must not be promoted from research because a recording shows a profitable sequence.

## Stage 1 — deterministic planner

Validate:

- PA pivot and zone identification;
- breakout buffer and retest tolerance;
- rejection/engulfing confirmation;
- tick rounding;
- fixed step and ATR step modes;
- hard quantity and pending-trigger caps;
- deterministic dedupe keys;
- SET-equity rejection of symmetric grids;
- SET-equity rejection of naked short ladders;
- insufficient/stale/unknown inputs fail closed.

## Stage 2 — virtual cycle runtime

Validate:

- arm requires a non-empty non-executable plan;
- crossing a level emits a virtual trigger once;
- price oscillation across the same level does not duplicate the trigger;
- multi-level gaps produce each crossed trigger once;
- PA invalidation terminates the cycle;
- basket `+R` target enters take-profit state;
- basket `-R` boundary enters stopped state;
- terminal state requires explicit reset;
- pause/resume transitions preserve the last observed price;
- durable snapshot recovery restores the plan and fired dedupe keys;
- restart behavior does not silently regenerate execution authority.

## Stage 3 — replay and adverse-path simulation

Required scenarios:

1. smooth one-way trend;
2. range/whipsaw through both sides of the anchor;
3. gap across multiple trigger levels;
4. quote duplication and out-of-order delivery;
5. spread widening;
6. exchange session close/reopen;
7. stale feed;
8. price-band/tick-size rejection;
9. partial fills and resting-order lifecycle;
10. ambiguous broker response followed by reconciliation;
11. loss sequence large enough to reach cycle stop;
12. a reversal after a clip-1-style fast trend.

Track trade count, turnover, gross/net exposure, drawdown, fees, slippage, profit factor, win/loss distribution, time in market and maximum simultaneous orders/positions. The repository provides deterministic parameter sweep, rolling walk-forward, seeded Monte Carlo trade-order stress, adverse oscillation/grid-whipsaw replay, gap-through-trigger checks, spread/slippage/commission sensitivity, maximum-exposure heatmaps and basket lifecycle metrics.

## Stage 4 — walk-forward/OOS

Use multiple market regimes and do not optimize on the entire history. Record parameter sets before each OOS interval. Reject promotion if performance depends on a single exceptional trend or if modest fee/slippage changes erase the edge.

## Stage 5 — MetaTrader reference

Compile `ea/ZKSATO_VideoDerived_PA_Grid.mq5` in MetaEditor and run Strategy Tester plus demo-account tests. Verify broker-specific minimum stop distance, lot step, pending-order limits, pending expiry, session gate, hedging/netting behavior (including fail-closed handling of foreign netting exposure), restart recovery, tester CSV statistics and every trade-server return code. Start with the checked-in `ea/presets/` files.

The reference EA must continue to reject `ACCOUNT_TRADE_MODE_REAL`.

## Stage 6 — Settrade Sandbox/UAT

Use the installed Settrade v2 SDK and the broker-provided Sandbox/UAT account. Validate only through the repository's trusted execution path:

- authoritative instrument metadata;
- market-session policy;
- quote freshness;
- tick/price-band checks;
- account/position/line-available state;
- idempotent client order IDs;
- explicit operator authorization;
- broker reconciliation after every ambiguous outcome.

## Promotion rule

Passing source tests is necessary but not sufficient. A separately authorized minimal live-equity canary is only considered after source validation, research evidence, Settrade UAT, broker/legal approval, production TLS/secrets/monitoring/DR evidence and operator sign-off.

Autonomous live-money execution is not a promotion stage and remains unsupported.
