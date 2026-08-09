# Issue triage

## Intake
Confirm issue type, affected revision/environment, reproduction, severity, sensitive-data sanitation, ownership, and whether broker/external evidence is involved.

## Priority
P0: active/unbounded exposure, execution-boundary/security compromise, durable corruption.
P1: high-likelihood safety/correctness issue or production blocker.
P2: significant defect/feature gap without immediate safety risk.
P3: improvement/docs/cleanup.

## Routing
Risk/execution/broker/auth/migration/TFEX issues receive explicit high-risk review. Security vulnerabilities use private reporting rather than normal issue disclosure.

## Closure
Record resolution, tests/evidence, affected release, rollout/rollback if relevant, and external follow-up that remains pending.
