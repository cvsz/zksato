# FAQ

## Can zksato run fully autonomous live trading?
No. Autonomous live-money execution is forbidden by repository policy. Live equity mutation requires deterministic server-side risk and explicit operator authorization.

## Is paper trading identical to SET matching?
No. The simulator is deterministic and useful for development, but it does not claim exchange queue priority, hidden liquidity, latency, or full microstructure fidelity.

## Is TFEX production execution enabled?
No. TFEX mutation remains sandbox/UAT-only until broker semantics and operational approvals are separately certified.

## Is Redis the source of truth?
No. Redis is optional coordination/rate-limit state. PostgreSQL is the durable correctness boundary when configured.

## Does a green source repo mean production-ready?
No. Broker permissions, UAT, exchange calendar/reference verification, TLS/secrets, monitoring, backup/restore, incident drills, capacity, legal/operational approval, and manual canary authorization are external evidence.

## Where is the API contract?
The running `/openapi.json` is authoritative; `docs/API-SPEC.md` documents intent and safety semantics.

## Why can readiness become false after restart?
Broker reconciliation readiness is a freshness assertion and must be re-established by a fresh broker snapshot after every non-paper restart.
