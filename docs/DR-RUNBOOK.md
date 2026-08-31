# Disaster recovery runbook

## Pre-requisites
- Kill switch activated (`ZKSATO_KILL_SWITCH=true`) or automation stopped
- No open live orders; if open, cancel through operator-approved flow only
- Backup target storage writable and verified

## Steps
1. Activate the kill switch and stop automation/broker mutations.
2. Capture logs, audit export, PostgreSQL status, Redis status, and broker snapshots.
3. Create a verified PostgreSQL backup with `scripts/backup_postgres.sh` when the database is readable.
4. Restore only into a verified isolated target using `CONFIRM_RESTORE=<target_env> scripts/restore_postgres.sh BACKUP.dump`.
5. Apply every migration in lexical order if restoring to an older schema version.
6. Start the API with live trading disabled (`ZKSATO_TRADING_MODE=paper`).
7. Verify `/health`, `/livez`, `/readyz`, audit hash-chain integrity, portfolio, local orders, and broker credentials.
8. Run broker reconciliation until `reconciliation_ready=true` with zero unresolved orders.
9. Run UAT/paper smoke tests and monitoring checks.
10. Re-enable manual operations only after incident/change approval. Autonomous live execution remains forbidden.

## Evidence to record
- Backup file path, size, checksum
- Restore target environment
- RPO (last transaction LSN / timestamp)
- RTO (restore duration)
- Migration result
- Reconciliation result
- `/readyz` status and failing checks if any
- Approver and timestamp

## Quarterly drill checklist
- [ ] Backup created and checksum verified
- [ ] Restore into isolated target successful
- [ ] All migrations applied cleanly
- [ ] API passes `/readyz` with live trading disabled
- [ ] Broker reconciliation converges with zero unresolved orders
- [ ] Paper smoke tests pass
- [ ] Monitoring/alerting restored
- [ ] Evidence archived with approver signature
