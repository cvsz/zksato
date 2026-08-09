# Acceptance criteria

A feature is acceptable only when applicable criteria are satisfied.

## Core
- implementation matches documented scope and API/domain contracts;
- positive, negative, and failure-path tests exist;
- restart/idempotency/concurrency behavior is covered when stateful;
- errors are explicit and do not silently widen authority;
- metrics/logs/audit evidence are sufficient to operate the feature.

## Trading-sensitive
- trusted risk context is computed server-side;
- stale/unknown prerequisites fail closed;
- autonomous live execution remains impossible;
- reconciliation/order identity cannot be bypassed;
- paper/UAT/live behavior is explicitly documented;
- broker-sensitive behavior has UAT evidence before being called certified.

## Data/migrations
- migration is additive/reversible where practical;
- forward/rollback/restore behavior is documented;
- durable evidence integrity is validated.

## Delivery
- required CI runs and passes on the final head;
- docs/feature matrix/ADR/runbook are updated;
- rollout and rollback are documented;
- external gates remain marked pending until evidence exists.
