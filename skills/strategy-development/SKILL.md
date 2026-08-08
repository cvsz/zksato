# Skill: strategy development

## Workflow
1. State hypothesis and deterministic rules.
2. Define required data/lookback/session assumptions.
3. Implement pure signal logic with typed parameters.
4. Add unit fixtures for entry/exit/hold edge cases.
5. Backtest with fees/slippage and no look-ahead.
6. Walk-forward/out-of-sample evaluate.
7. Paper trade before UAT promotion.

## Rule
A strategy creates signals; it never owns broker authority.
