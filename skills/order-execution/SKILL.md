# Skill: order execution and reconciliation

## Workflow
Typed intent → persisted idempotency key → risk approval → environment/authorization gate → broker call → map result → persist events → reconcile until terminal.

## Critical cases
Timeout after submit, duplicate retry, partial fill, cancel/replace race, broker rejection, process restart, broker/local drift.

## Output
State-machine behavior, tests, audit correlation IDs, retry/ambiguity policy, rollback notes.
