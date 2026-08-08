# Strategy framework

## Current strategies
EMA crossover, RSI mean reversion, breakout.

## Target plugin contract
Typed `StrategyConfig` + immutable strategy version + required lookback + `evaluate(history, context) -> Signal/Hold`.

## Rules
Pure/deterministic where possible, no broker calls, no secret access, no direct risk override, explicit warmup/session behavior, timestamp-aware inputs, versioned parameters.

## Promotion gates
Research hypothesis → unit fixtures → historical backtest → out-of-sample/walk-forward → paper → UAT. A strong backtest alone is insufficient.

## Reproducibility
Store code version, parameters, data version/range, fees/slippage model, seed where relevant, and generated report.
