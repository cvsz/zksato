# Deployment

## Current local deployment
`docker compose up --build -d` exposes the API/dashboard on port `9569`.

## Target environments
- dev: paper, synthetic/local data permitted.
- UAT: Settrade simulated environment, test credentials, no production account secrets.
- prod: explicit production config, authenticated operators, durable state, reconciliation, observability, backups, and live controls.

## Production shape
Reverse proxy/TLS → app/API replicas → PostgreSQL → Redis → workers/reconciliation → metrics/logging. Secrets supplied by managed secret store/environment injection, never image layers.

## Deployment steps
Build immutable image; scan/test; backup/check DB; run migrations; deploy; readiness/health; smoke `/health` on 9569; verify broker/feed connectivity; verify risk/kill switch/config; monitor; rollback on gate failure.

## Rollback
Application rollback must account for schema compatibility. If a broker-mutating release is rolled back, reconcile broker state before resuming automation.
