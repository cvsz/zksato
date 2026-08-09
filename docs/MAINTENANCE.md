# Maintenance

## Routine
Review dependency updates, vulnerabilities, backups, restore drills, certificates/secrets, account permissions, reference/calendar data, SLO trends, database growth, outbox/audit backlog, and stale branches/artifacts.

## Before maintenance
Define impact, maintenance window, backup, rollback, broker/execution state, kill-switch expectations, monitoring, and operator communication.

## During
Avoid schema/runtime skew, apply migrations in documented order, keep evidence, and do not weaken safety gates for convenience.

## After
Verify `/livez`, `/readyz`, `/health`, metrics, audit integrity, broker reconciliation freshness, and relevant synthetic/paper tests. Record deviations and follow-up work.
