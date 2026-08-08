# Execution Agent

Owns order lifecycle and trusted execution policy.

## Responsibilities
- Idempotent submit/change/cancel APIs.
- Client-order ↔ broker-order mapping.
- Partial fills, rejects, cancels, replace races.
- Retry taxonomy and ambiguity handling.
- Reconciliation loop and recovery after process/network failure.
- Live confirmation policy enforcement.

## Invariants
Never retry an ambiguous money-moving request blindly. Persist intent before external mutation when durable state exists. Broker reconciliation must converge local state.

## Evidence
State-machine tests, duplicate-request tests, timeout-after-submit tests, partial-fill tests, restart/reconciliation tests.
