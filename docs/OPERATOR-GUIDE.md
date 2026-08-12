# Operator guide

## Start
Read `PRODUCTION-READINESS.md`, `OPERATIONS.md`, `SLO.md`, `ONCALL.md`, and `INCIDENT-RESPONSE.md`. Confirm environment and mode before any mutation.

## Routine checks
- `/livez`, `/readyz`, `/health`, `/metrics`;
- database/Redis health;
- market feed freshness/session/reference state;
- reconciliation freshness/unresolved orders;
- audit-chain validity;
- open orders/portfolio/account snapshots;
- kill-switch and alert status.

## Change/release
Use deployment/rollback/release checklists, apply migrations in order, and retain evidence. UAT/production credentials are environment-scoped and must not appear in PRs/logs.

## Incident
Stop automation and engage kill switch before investigating any suspected unintended exposure. Verify broker state independently. Follow the incident runbook and preserve sanitized evidence.
