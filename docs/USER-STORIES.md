# User stories

## Strategy operator
- As a strategy operator, I can ingest/replay historical bars and compare deterministic strategy evidence without broker mutation.
- I can register immutable strategy versions and inspect run history/drift before requesting promotion.
- I can run paper automation and pause/resume it without granting live authority.

## Order approver
- As an order approver, I can inspect intent and trusted risk context before granting a bounded one-time live equity approval.
- I can cancel eligible open orders through controlled APIs and audit the result.

## Risk administrator
- As a risk administrator, I can configure limits/kill switch/reference requirements and see why a trade was approved or rejected.
- I can verify account/session/reference/reconciliation prerequisites before live readiness.

## Auditor
- As an auditor, I can inspect order events, fills, risk evaluations, account snapshots, strategy evidence, and hash-linked audit records without mutation authority.

## Platform operator
- As an operator, I can check liveness/readiness/metrics, perform migrations/backups/restores, run DR/performance/UAT evidence workflows, and produce release/readiness evidence.

## Maintainer
- As a maintainer, I can use standardized issue/PR/document templates so high-risk changes consistently include validation, rollout, rollback, and security evidence.
