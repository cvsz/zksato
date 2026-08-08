# Disaster recovery

## Recovery priorities
1. Prevent new unsafe orders.
2. Independently establish broker positions/open orders.
3. Restore durable database/audit state.
4. Reconcile broker ↔ local state.
5. Restore market feed and read-only monitoring.
6. Resume automation only after explicit validation.

## Required capabilities
Automated PostgreSQL backups, encrypted off-host copies, restore drills, documented RPO/RTO, configuration/secret recovery, deployment artifact retention, reconciliation-from-broker procedure.

## Scenarios
Host loss, DB corruption, Redis loss, broker outage, market-data outage, credential rotation, bad migration, partial deployment, network partition.

Redis loss must not destroy durable trading truth. A restored DB is not sufficient until broker reconciliation completes.
