# Deployment

## Current local deployment
`docker compose up --build -d` exposes the API/dashboard on port `9569`.

### Local Shared Infrastructure: `zpostgresql` & `zredis`
For developers sharing existing local database and cache services:
- **PostgreSQL**: Connect to local container `zpostgresql` via `zPostgreSQL_network` (or direct IP `172.26.0.5:5432` from the host).
  - Configure `ZKSATO_DATABASE_URL=postgresql+psycopg://<username>:<password>@zpostgresql:5432/<db_name>` (or target database).
- **Redis**: Connect to local container `zredis` (`zRedis`) via `zPostgreSQL_network` (or direct IP `172.26.0.3:6379`).
  - Configure `ZKSATO_REDIS_URL=redis://<acl_user>:<password>@zredis:6379/0`.

## Production shape & Ingress (`https://zksato.zeaz.dev/*`)
Reverse proxy/TLS (NGINX/Let's Encrypt) → app/API replicas (`https://zksato.zeaz.dev/*`) → PostgreSQL → Redis → workers/reconciliation → metrics/logging. Secrets supplied by managed secret store/environment injection, never image layers.

Unified public ingress routing:
- Web Application: `https://zksato.zeaz.dev/`
- API & Engine Endpoints: `https://zksato.zeaz.dev/v1/*` (e.g. `/v1/orders`, `/v1/risk`, `/v1/market`, `/v1/agent-os/skills`)
- Health & Monitoring: `https://zksato.zeaz.dev/health`, `https://zksato.zeaz.dev/livez`, `https://zksato.zeaz.dev/readyz`, `https://zksato.zeaz.dev/metrics`
- Market Terminal: `https://zksato.zeaz.dev/v1/market/terminal`
- Dashboard: `https://zksato.zeaz.dev/dash/`

## Deployment steps
Build immutable image; scan/test; backup/check DB; run migrations; deploy; readiness/health; smoke `/health` on 9569; verify broker/feed connectivity; verify risk/kill switch/config; monitor; rollback on gate failure.

## Environment file validation
The `deploy/deploy.sh` script validates environment files before sourcing:
- Permission check (recommends 600 or 400)
- Injection pattern detection (rejects `;`, `$()`, backticks, `&&`, `||`, pipes)
- Required secrets validation (postgres_password, redis_password, session_secret, api_keys)

## Rollback
Application rollback must account for schema compatibility. If a broker-mutating release is rolled back, reconcile broker state before resuming automation.
