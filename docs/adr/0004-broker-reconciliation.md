# ADR-0004: Broker reconciliation as live convergence mechanism

Status: Accepted target

## Decision
Treat broker order/deal/position state as external truth for live reconciliation. Local unknown/ambiguous outcomes are repaired through polling/subscription evidence, never blind retry.

## Consequences
Requires durable mappings and reconciliation workers; significantly reduces duplicate/phantom order risk.
