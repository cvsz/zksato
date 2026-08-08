# Backtesting and research validation

## Principles
Same strategy rules as automation; no look-ahead; timestamp/session correctness; deterministic replay; explicit fees/slippage/fill assumptions.

## Required report
Dataset/range, strategy/code/parameter versions, capital/sizing, fees/slippage, return, max drawdown, trade count, win/loss distribution, turnover/exposure, equity curve, benchmark/context, caveats.

## Advanced validation
Walk-forward, out-of-sample, parameter sensitivity, stress/gap scenarios, missing-data tests, Monte Carlo/order resampling where meaningful.

## Promotion
Backtest evidence is necessary but never sufficient for UAT/live promotion; paper behavior and broker UAT remain required.
