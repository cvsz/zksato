# Review guide

## General
Check scope, correctness, tests, API/data compatibility, docs, operability, maintainability, and whether the PR head being reviewed is the head validated by CI.

## High-risk review
Ask:
- can any path bypass `RiskEngine`/`TradingService`?
- can retries/restarts duplicate economic orders?
- can stale/unknown data authorize action?
- does broker reconciliation converge and fail closed on ambiguity?
- are credentials/account data protected?
- are migrations safe and ordered?
- is money-moving behavior deterministic and audited?
- is TFEX kept separate and UAT-only unless certified?

## Evidence
Do not accept checkbox assertions when direct test/UAT/deployment evidence is required. Plan-gated GitHub features and broker permissions must be represented as external state.

## Merge
Resolve P0/P1 review findings, rerun required checks on final head, and verify rollout/rollback for operational changes.
