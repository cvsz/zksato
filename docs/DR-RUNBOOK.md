# Disaster recovery runbook

1. Activate the kill switch and stop automation/broker mutations.
2. Capture logs, audit export, PostgreSQL status, Redis status, and broker snapshots.
3. Create a verified PostgreSQL backup with `scripts/backup_postgres.sh` when the database is readable.
4. Restore only into a verified target using `CONFIRM_RESTORE=zksato scripts/restore_postgres.sh BACKUP.dump`.
5. Apply every migration in lexical order.
6. Start the API with live trading disabled.
7. Verify `/health`, audit hash-chain integrity, portfolio, local orders, and broker credentials.
8. Run broker reconciliation until `reconciliation_ready=true` with zero unresolved orders.
9. Run UAT/paper smoke tests and monitoring checks.
10. Re-enable manual operations only after incident/change approval. Autonomous live execution remains forbidden.

Quarterly recovery evidence should record RPO, RTO, backup checksum, restore target, migration result, reconciliation result, and approver.
