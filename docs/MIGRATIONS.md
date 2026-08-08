# Database migrations

## Policy
Schema changes are version-controlled, reviewed, tested on representative data, and applied through deployment automation.

## Trading-sensitive migrations
Changes to orders, fills, positions, idempotency, risk decisions, approvals, or audit require compatibility analysis, backup, forward/rollback or restore strategy, and post-migration reconciliation checks.

## Zero/low-downtime pattern
Expand schema → deploy compatible code → backfill/verify → switch reads/writes → contract old schema later. Avoid destructive one-step migrations on live trading records.
