# Reliability engineering

## Principles
Correctness over availability for money-moving paths; degraded prerequisites should stop new execution rather than guess. Optional subsystems such as notifications must not block the trading path.

## Failure domains
Database, Redis coordination, broker API, realtime market feed, notification endpoint, process restart, container/host, network, and operator configuration.

## Required behavior
- durable order/fill/risk/audit state survives restart;
- freshness-only broker reconciliation state does not survive restart;
- ambiguous broker outcomes become reconciliation work, not automatic retry execution;
- stale/unknown market data fails closed;
- background retries are bounded and observable;
- recovery is idempotent and tested.

## Evidence
Use resilience tests, DR drill, backup/restore checksum, readiness/health metrics, incident reports, and measured RTO/RPO. See `SLO.md`, `DR-RUNBOOK.md`, and `CAPACITY-PLANNING.md`.
