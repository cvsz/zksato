# ADR-0001: Risk-first execution boundary

Status: Accepted

## Context
Strategies, dashboards, and AI can produce unsafe actions if they own broker authority.

## Decision
Every order passes deterministic RiskEngine and TradingService before Broker. Autonomous live execution by strategies/AI is forbidden; live mutation requires explicit authenticated operator authorization.

## Consequences
More explicit interfaces and approval latency, but stronger safety, auditability, and testability.
