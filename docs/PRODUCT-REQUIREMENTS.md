# Product requirements

## Product goal
Provide a reliable operator-controlled automated trading platform for SET and TFEX with deterministic strategies, independent risk controls, broker integration, auditable execution, research/backtesting, and a realtime operations dashboard.

## Personas
- Operator/trader: monitors, approves, stops, and reconciles trading.
- Strategy developer: develops deterministic signals and backtests.
- Risk administrator: owns limits and kill switches.
- Platform operator: deploys, observes, backs up, and restores.
- Auditor/reviewer: traces every decision and order lifecycle.

## Functional requirements
Market data, strategy engine, risk engine, paper/UAT execution, portfolio/P&L, order lifecycle, alerts, dashboard, historical backtesting, durable audit, Settrade equity, TFEX domain, authentication/RBAC, observability, DR, and controlled releases.

## Non-functional requirements
Correctness before throughput; fail-closed safety; deterministic money-moving logic; restart-safe idempotency; broker reconciliation; clear environment separation; secrets protection; low operational ambiguity; testability; documented rollback.

## Explicit non-goal
An LLM or autonomous agent with unrestricted authority to place live-money orders.
