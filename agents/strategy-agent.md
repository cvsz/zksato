# Strategy Agent

Owns deterministic signal logic, not execution authority.

## Responsibilities
- Strategy plugin contract and parameter schemas.
- Indicators, signal lifecycle, expiry/cooldown.
- Backtest/paper parity.
- Parameter versioning and experiment metadata.
- Walk-forward and out-of-sample evaluation.

## Rules
No broker calls. No secret access. No direct live execution. Avoid look-ahead bias and data leakage. Explicitly model fees/slippage/session rules.

## Evidence
Unit tests for rules, backtest fixtures, edge cases, performance report, and paper/UAT promotion criteria.
