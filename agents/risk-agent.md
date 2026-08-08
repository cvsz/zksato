# Risk Agent

Owns deterministic independent risk controls.

## Scope
- Position sizing and stop-risk budget.
- Max position/gross/net/sector/symbol exposure.
- Daily loss, drawdown, order count/rate/notional limits.
- Stale-price/slippage/price-band/session guards.
- Kill switch, account allow-list, manual approval policies.
- TFEX margin and contract risk in collaboration with TFEX agent.

## Invariants
Risk rejection prevents broker invocation. Unknown required inputs fail closed. Client/dashboard cannot override server policy.

## Tests
Boundary values, missing inputs, malformed prices, stale data, repeated orders, drawdown transitions, kill-switch behavior, recovery after restart.
