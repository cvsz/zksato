# Environments

## Local development (`dev`)
Default `paper`, local/memory or Docker PostgreSQL/Redis, no production credentials. Port `9569`.

**Required secrets/credentials:**
- None for paper mode
- `ZKSATO_SETTRADE_APP_ID`, `ZKSATO_SETTRADE_APP_SECRET`, `ZKSATO_SETTRADE_BROKER_ID`, `ZKSATO_SETTRADE_ACCOUNT_NO`, `ZKSATO_SETTRADE_PIN` — sandbox only, never production
- `ZKSATO_SESSION_SECRET` — required if `ZKSATO_AUTH_REQUIRED=true`
- `ZKSATO_API_KEYS` — required if `ZKSATO_AUTH_REQUIRED=true`
- `ZKSATO_NOTIFICATION_WEBHOOK_URL` — optional
- `ZKSATO_TELEGRAM_BOT_TOKEN`, `ZKSATO_TELEGRAM_CHAT_ID` — optional
- `ZKSATO_TRADINGVIEW_WEBHOOK_SECRET` — optional
- `ZKSATO_PREDICTION_CLOB_API_KEY`, `ZKSATO_PREDICTION_CLOB_API_SECRET`, `ZKSATO_PREDICTION_CLOB_PASSPHRASE` — optional, prediction sandbox only

**Constraints:**
- Live trading is forbidden
- Production credentials are never allowed
- Auth is optional but recommended for multi-user testing

For unlock procedures, see `UNLOCK-RELEASE.md`.

## Test/CI (`test`)
Ephemeral services and synthetic credentials/data only. Normal CI excludes broker UAT and destructive production actions.

**Required secrets/credentials:**
- `ZKSATO_TEST_DATABASE_URL` — ephemeral PostgreSQL
- `ZKSATO_TEST_REDIS_URL` — ephemeral Redis
- `ZKSATO_SETTRADE_*` — sandbox/UAT credentials from CI secrets only, never production
- `ZKSATO_SESSION_SECRET` — ephemeral random value
- `ZKSATO_API_KEYS` — synthetic test keys

**Constraints:**
- Live trading is forbidden
- Production credentials are never allowed
- Broker UAT tests must use dedicated UAT credentials, not production
- All secrets must come from CI secret store, never hardcoded

For unlock procedures, see `UNLOCK-RELEASE.md`.

## Broker UAT/sandbox (`uat`)
Uses broker-issued non-production credentials and explicit certification evidence. UAT proves only the tested account/environment/revision and does not imply production permission.

**Schedule constraint:**
- Best availability: Thursday and Friday, 09:00-17:00 Thailand time
- Supports Equity (Day Session) and Derivatives (Day & Night Session)
- Does NOT support Offline Order
- No guarantee outside the above hours

**Required secrets/credentials:**
- `ZKSATO_SETTRADE_APP_ID` — UAT app ID from broker
- `ZKSATO_SETTRADE_APP_SECRET` — UAT app secret from broker
- `ZKSATO_SETTRADE_BROKER_ID` — UAT broker ID from broker
- `ZKSATO_SETTRADE_ACCOUNT_NO` — UAT account number from broker
- `ZKSATO_SETTRADE_PIN` — UAT PIN from broker
- `ZKSATO_SETTRADE_APP_CODE=ALGO_EQ` — required
- `ZKSATO_AUTH_REQUIRED=true` — mandatory
- `ZKSATO_API_KEYS` — operator keys for RBAC
- `ZKSATO_SESSION_SECRET` — long random secret for session signing
- `ZKSATO_TRUSTED_HOSTS` — explicit host allowlist
- `ZKSATO_DATABASE_URL` — durable PostgreSQL required
- `ZKSATO_REDIS_URL` — Redis coordination required

**Constraints:**
- Live trading is forbidden (sandbox only)
- Production credentials are never allowed
- `settradesdkv2_config.txt` must use `environment=uat`
- Strict reference data and market session enforcement are required
- No production account numbers or broker IDs

For unlock procedures, see `UNLOCK-RELEASE.md`.

## Production (`prod`)
Requires authenticated TLS deployment, PostgreSQL correctness store, Redis coordination where configured, managed secrets, verified reference/calendar data, monitoring/alerts, backups/restore evidence, incident/rollback readiness, broker/legal/operational permission, reconciliation readiness, and explicit manual canary authorization.

**Required secrets/credentials:**
- `ZKSATO_SETTRADE_APP_ID` — production app ID from broker
- `ZKSATO_SETTRADE_APP_SECRET` — production app secret from broker (managed secret, never in env file)
- `ZKSATO_SETTRADE_BROKER_ID` — production broker ID from broker
- `ZKSATO_SETTRADE_ACCOUNT_NO` — production account number from broker
- `ZKSATO_SETTRADE_PIN` — production PIN from broker (managed secret, never in env file)
- `ZKSATO_SETTRADE_APP_CODE=ALGO_EQ` — required
- `ZKSATO_AUTH_REQUIRED=true` — mandatory
- `ZKSATO_API_KEYS` — operator keys for RBAC (managed secret)
- `ZKSATO_SESSION_SECRET` — long random secret for session signing (managed secret)
- `ZKSATO_TRUSTED_HOSTS` — explicit host allowlist
- `ZKSATO_DATABASE_URL` — durable PostgreSQL required
- `ZKSATO_REDIS_URL` — Redis coordination required
- `ZKSATO_LIVE_CONFIRMATION_TOKEN` — execution control secret (managed secret, never in frontend/logs/CI)
- `ZKSATO_NOTIFICATION_WEBHOOK_URL` — optional webhook
- `ZKSATO_TELEGRAM_BOT_TOKEN`, `ZKSATO_TELEGRAM_CHAT_ID` — optional
- `ZKSATO_TRADINGVIEW_WEBHOOK_SECRET` — optional
- `ZKSATO_PREDICTION_CLOB_API_KEY`, `ZKSATO_PREDICTION_CLOB_API_SECRET`, `ZKSATO_PREDICTION_CLOB_PASSPHRASE` — optional

**Constraints:**
- Kill switch MUST be enabled initially (`ZKSATO_KILL_SWITCH=true`)
- Live trading requires `POST /v1/production/readiness` returning `ready_for_manual_canary=true`
- Live orders require explicit operator authorization via `/v1/live-approvals`
- Four-eyes approval is mandatory
- Account allow-list is mandatory
- Strict reference data and market session enforcement are mandatory
- Legacy live token is forbidden
- Production credentials must never appear in dev/test/uat
- All broker credentials must be managed secrets, never committed

For unlock procedures, see `UNLOCK-RELEASE.md`.

## GitHub environments
Target `uat` and `production` environments with protected secrets/reviewers where supported. Their actual existence/settings are external GitHub state and must be verified rather than inferred from workflow YAML.

**Required GitHub secrets:**
- `ZKSATO_SETTRADE_APP_ID` — environment-scoped (UAT or production)
- `ZKSATO_SETTRADE_APP_SECRET` — environment-scoped
- `ZKSATO_SETTRADE_BROKER_ID` — environment-scoped
- `ZKSATO_SETTRADE_ACCOUNT_NO` — environment-scoped
- `ZKSATO_SETTRADE_PIN` — environment-scoped
- `ZKSATO_SESSION_SECRET` — environment-scoped
- `ZKSATO_API_KEYS` — environment-scoped
- `ZKSATO_LIVE_CONFIRMATION_TOKEN` — production only
- `ZKSATO_NOTIFICATION_WEBHOOK_URL` — optional
- `ZKSATO_TELEGRAM_BOT_TOKEN`, `ZKSATO_TELEGRAM_CHAT_ID` — optional
- `ZKSATO_TRADINGVIEW_WEBHOOK_SECRET` — optional

**Constraints:**
- UAT and production secrets must be isolated per GitHub environment
- Production secrets must have protected branch and reviewer requirements
- Secrets must never be logged or exposed in workflow outputs
