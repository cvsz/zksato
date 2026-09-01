# Unlock and Release Runbook

This document defines the environment-specific unlock and release procedures for zksato.
"Unlock" means transitioning from the default safe state (`paper` + `kill_switch=false`) to a more permissive trading or testing state.
"Release" means promoting code or configuration changes through environments to production.

## Environment definitions

| Environment | Purpose | Trading mode default | Live trading | Authentication |
|-------------|---------|----------------------|--------------|----------------|
| `dev` | Local/feature development | `paper` | Off | Optional |
| `test` | CI/ephemeral integration tests | `paper` | Off | Optional |
| `uat` | Broker sandbox certification | `sandbox` | Off | Required for broker access |
| `prod` | Production trading | `live` | Explicitly enabled | Required |

## Unlock matrix

| Unlock action | dev | test | uat | prod |
|---------------|-----|------|-----|------|
| Disable kill switch | Allowed | Allowed | Allowed | Allowed (operator only) |
| Enable automation | Allowed | Allowed | Allowed | Allowed (operator only) |
| Switch to `sandbox` mode | Allowed | Allowed | Allowed | Forbidden |
| Switch to `live` mode | Forbidden | Forbidden | Forbidden | Allowed (operator + readiness) |
| Enable live trading | Forbidden | Forbidden | Forbidden | Allowed (operator + readiness) |
| Prediction live trading | Forbidden | Forbidden | Forbidden | Allowed (operator only) |
| Skip live confirmation | Forbidden | Forbidden | Forbidden | Forbidden |

## 1. dev — Unlock procedure

### 1.1 Default safe state
```bash
ZKSATO_ENVIRONMENT=dev
ZKSATO_TRADING_MODE=paper
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_LIVE_REQUIRES_CONFIRMATION=true
ZKSATO_PREDICTION_ENABLE_LIVE=false
```

### 1.2 Unlock to paper automation
For local strategy development and paper auto-execution:

```bash
# In .env
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=true
ZKSATO_KILL_SWITCH=false
```

Restart the API:
```bash
docker compose restart api
```

Verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.trading_mode, .kill_switch, .automation_enabled'
```

Expected output:
```json
"paper"
false
true
```

### 1.3 Unlock to sandbox mode (broker UAT prep)
For local testing against broker sandbox credentials:

```bash
# In .env
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=...
ZKSATO_SETTRADE_APP_SECRET=...
ZKSATO_SETTRADE_BROKER_ID=...
ZKSATO_SETTRADE_ACCOUNT_NO=...
ZKSATO_SETTRADE_PIN=...
ZKSATO_SETTRADE_APP_CODE=ALGO_EQ
ZKSATO_KILL_SWITCH=false
ZKSATO_AUTH_REQUIRED=true
ZKSATO_API_KEYS=risk-random-key:risk_admin;order-random-key:order_approver
ZKSATO_SESSION_SECRET=<long-random-secret>
```

Restart and verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.trading_mode, .settrade_configured'
```

### 1.4 Re-lock (return to safe state)
```bash
# In .env
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
```

Remove broker credentials if no longer needed:
```bash
# Comment out or clear in .env
# ZKSATO_SETTRADE_APP_ID=
# ZKSATO_SETTRADE_APP_SECRET=
# ZKSATO_SETTRADE_PIN=
```

## 2. test — Unlock procedure

### 2.1 Default safe state
```bash
ZKSATO_ENVIRONMENT=test
ZKSATO_TRADING_MODE=paper
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
```

### 2.2 Unlock to paper automation (CI)
For integration tests that exercise the full trading pipeline:

```bash
ZKSATO_ENVIRONMENT=test
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=true
ZKSATO_KILL_SWITCH=false
ZKSATO_PAPER_MATCH_RESTING_LIMITS=true
ZKSATO_PAPER_PRICE_IMPROVEMENT=false
```

### 2.3 Unlock to sandbox (broker integration tests)
For CI jobs that test broker integration against sandbox:

```bash
ZKSATO_ENVIRONMENT=test
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=${SETTRADE_UAT_APP_ID}
ZKSATO_SETTRADE_APP_SECRET=${SETTRADE_UAT_APP_SECRET}
ZKSATO_SETTRADE_BROKER_ID=${SETTRADE_UAT_BROKER_ID}
ZKSATO_SETTRADE_ACCOUNT_NO=${SETTRADE_UAT_ACCOUNT}
ZKSATO_SETTRADE_PIN=${SETTRADE_UAT_PIN}
ZKSATO_KILL_SWITCH=false
```

**Constraint:** Never use production broker credentials in `test` environment.

### 2.4 Re-lock
```bash
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
```

## 3. uat — Unlock procedure

### 3.1 Default safe state
```bash
ZKSATO_ENVIRONMENT=uat
ZKSATO_TRADING_MODE=sandbox
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
```

### 3.2 Unlock to sandbox certification
UAT is the **only** environment where broker sandbox credentials are used.

**Schedule constraint:**
- Best availability: Thursday and Friday, 09:00-17:00 Thailand time
- Supports Equity (Day Session) and Derivatives (Day & Night Session)
- Does NOT support Offline Order
- No guarantee outside the above hours

```bash
ZKSATO_ENVIRONMENT=uat
ZKSATO_TRADING_MODE=sandbox
ZKSATO_SETTRADE_APP_ID=<UAT app id>
ZKSATO_SETTRADE_APP_SECRET=<UAT secret>
ZKSATO_SETTRADE_BROKER_ID=<UAT broker id>
ZKSATO_SETTRADE_ACCOUNT_NO=<UAT account>
ZKSATO_SETTRADE_PIN=<UAT pin>
ZKSATO_SETTRADE_APP_CODE=ALGO_EQ
ZKSATO_KILL_SWITCH=false
ZKSATO_AUTH_REQUIRED=true
ZKSATO_API_KEYS=<operator keys>
ZKSATO_SESSION_SECRET=<long-random-secret>
ZKSATO_STRICT_REFERENCE_DATA=true
ZKSATO_ENFORCE_MARKET_SESSIONS=true
```

Restart and verify broker connectivity:
```bash
curl -fsS http://127.0.0.1:9569/v1/uat/account
```

### 3.3 UAT exit criteria
Before promoting to production:
- [ ] Account lookup succeeds
- [ ] Portfolio lookup agrees with broker
- [ ] One limit buy can be submitted and cancelled
- [ ] Filled orders appear in local response mapping
- [ ] Broker order numbers are captured
- [ ] Rejected orders return understandable errors
- [ ] Risk rejection occurs before broker submission
- [ ] No production credentials are present

### 3.4 Re-lock
```bash
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
```

Clear UAT credentials:
```bash
# ZKSATO_SETTRADE_APP_ID=
# ZKSATO_SETTRADE_APP_SECRET=
# ZKSATO_SETTRADE_PIN=
```

## 4. prod — Unlock procedure

### 4.1 Default safe state
```bash
ZKSATO_ENVIRONMENT=prod
ZKSATO_TRADING_MODE=paper
ZKSATO_KILL_SWITCH=true
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
```

**Production starts with kill switch ACTIVE.** This is the safest default for a production deployment.

### 4.2 Pre-unlock checklist
Before unlocking production, complete ALL of the following:

- [ ] All UAT exit criteria are met
- [ ] `POST /v1/production/readiness` returns `ready_for_manual_canary=true`
- [ ] Durable PostgreSQL is configured and healthy
- [ ] Redis coordination is configured and healthy
- [ ] Authentication/RBAC is enabled
- [ ] At least one operator API key is configured
- [ ] Session secret is configured
- [ ] Trusted hosts are explicitly configured
- [ ] Legacy live token is disabled
- [ ] Live confirmation is required
- [ ] Four-eyes approval is enabled
- [ ] Account allow-list is configured
- [ ] Strict reference data is enabled
- [ ] Market session enforcement is enabled
- [ ] Settrade production credentials are configured
- [ ] Broker reconciliation has converged
- [ ] Audit chain verifies
- [ ] TLS ingress is verified
- [ ] Managed secrets are verified
- [ ] Backup/restore drill is complete
- [ ] Monitoring and alerts are verified
- [ ] Incident response and escalation path are verified
- [ ] Deployment rollback procedure is ready
- [ ] Capacity/SLO evidence is verified
- [ ] Time synchronization is verified
- [ ] Market data failover is verified
- [ ] Data retention policy is verified
- [ ] Release artifact digest is verified
- [ ] Manual canary is explicitly authorized

### 4.3 Unlock sequence

**Step 1 — Disable kill switch**
```bash
# In .env (or secrets manager)
ZKSATO_KILL_SWITCH=false
```

Restart and verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.kill_switch'
# Expected: false
```

**Step 2 — Enable live trading**
```bash
ZKSATO_TRADING_MODE=live
ZKSATO_LIVE_TRADING_ENABLED=true
ZKSATO_LIVE_REQUIRES_CONFIRMATION=true
ZKSATO_REQUIRE_DISTINCT_APPROVER=true
```

Restart and verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.trading_mode, .live_trading_enabled, .kill_switch'
```

Expected:
```json
"live"
true
false
```

**Step 3 — Execute manual canary**
The first live order is a manual canary with minimal exposure:

1. Operator creates a live approval:
   ```bash
   curl -X POST http://127.0.0.1:9569/v1/live-approvals \
     -H "X-API-Key: $RISK_ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{"intent": {"side": "buy", "symbol": "AOT", "quantity": 100, "price": 0.01}}'
   ```

2. Operator places the order with approval ID:
   ```bash
   curl -X POST http://127.0.0.1:9569/v1/orders \
     -H "X-API-Key: $ORDER_APPROVER_KEY" \
     -H "X-Live-Approval-Id: <approval_id>" \
     -H "Content-Type: application/json" \
     -d '{"intent": {"side": "buy", "symbol": "AOT", "quantity": 100, "price": 0.01}}'
   ```

3. Verify:
   - Order appears in `/v1/orders`
   - Broker state matches local state
   - Reconciliation converges
   - Audit trail captures the event

**Step 4 — Enable automation (optional, after canary success)**
```bash
ZKSATO_AUTOMATION_ENABLED=true
```

### 4.5 Unlock prediction live trading (optional)
```bash
ZKSATO_PREDICTION_ENABLE_LIVE=true
```

Verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.prediction_enable_live'
```

### 4.6 Re-lock (emergency)
```bash
# Immediate kill switch activation
ZKSATO_KILL_SWITCH=true
```

Or via environment:
```bash
export ZKSATO_KILL_SWITCH=true
docker compose restart api
```

Verify:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.kill_switch'
# Expected: true
```

## 5. Release procedures

### 5.1 dev → test promotion
```bash
git push origin main
```

CI runs automatically on `main`. Merge only when:
- `ruff check .` passes
- `pytest` passes
- No unresolved P0/P1 issues

### 5.2 test → uat promotion
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Tag triggers deployment to UAT environment. Verify:
- UAT broker connectivity
- UAT exit criteria (Section 3.3)
- Reconciliation converges
- No production credentials in UAT

### 5.3 uat → prod promotion
Requires:
- All UAT exit criteria met
- `POST /v1/production/readiness` returns `ready_for_manual_canary=true`
- Explicit operator authorization
- Approved release notes and rollback plan

Deploy during agreed maintenance window:
```bash
docker compose pull
docker compose up --build -d
```

Verify:
```bash
curl -fsS http://127.0.0.1:9569/health
curl -fsS http://127.0.0.1:9569/v1/config
curl -fsS http://127.0.0.1:9569/readyz
```

### 5.4 Rollback procedures

#### dev rollback
```bash
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
# Clear sandbox credentials if present
# ZKSATO_SETTRADE_APP_ID=
# ZKSATO_SETTRADE_APP_SECRET=
# ZKSATO_SETTRADE_PIN=
docker compose restart api
```

#### test rollback
```bash
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
# Clear test/UAT credentials from CI secrets
docker compose restart api
```

#### uat rollback
```bash
ZKSATO_TRADING_MODE=paper
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_KILL_SWITCH=false
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
# Clear UAT broker credentials
# ZKSATO_SETTRADE_APP_ID=
# ZKSATO_SETTRADE_APP_SECRET=
# ZKSATO_SETTRADE_BROKER_ID=
# ZKSATO_SETTRADE_ACCOUNT_NO=
# ZKSATO_SETTRADE_PIN=
docker compose restart api
```

#### prod rollback
```bash
# Immediate kill switch activation
ZKSATO_KILL_SWITCH=true
# Revert to safe paper mode
ZKSATO_TRADING_MODE=paper
ZKSATO_LIVE_TRADING_ENABLED=false
ZKSATO_AUTOMATION_ENABLED=false
ZKSATO_PREDICTION_ENABLE_LIVE=false
docker compose restart api
```

Verify rollback:
```bash
curl -fsS http://127.0.0.1:9569/v1/config | jq '.trading_mode, .kill_switch, .live_trading_enabled'
```

## 6. Quick reference

### Unlock commands by environment

| Environment | Unlock to | Command |
|-------------|-----------|---------|
| dev | paper automation | `ZKSATO_TRADING_MODE=paper ZKSATO_AUTOMATION_ENABLED=true ZKSATO_KILL_SWITCH=false` |
| dev | sandbox | `ZKSATO_TRADING_MODE=sandbox` + broker credentials |
| test | paper automation | `ZKSATO_TRADING_MODE=paper ZKSATO_AUTOMATION_ENABLED=true` |
| test | sandbox | `ZKSATO_TRADING_MODE=sandbox` + UAT broker credentials |
| uat | sandbox cert | `ZKSATO_TRADING_MODE=sandbox` + UAT broker credentials |
| prod | live | `ZKSATO_TRADING_MODE=live ZKSATO_LIVE_TRADING_ENABLED=true ZKSATO_KILL_SWITCH=false` |
| prod | prediction live | `ZKSATO_PREDICTION_ENABLE_LIVE=true` |

### Emergency re-lock (all environments)
```bash
ZKSATO_KILL_SWITCH=true
docker compose restart api
```

## 7. Constraints

- Autonomous live-money execution is **forbidden** in all environments.
- Live orders require **explicit operator authorization** at the trusted server boundary.
- No component may bypass `RiskEngine` or `TradingService`.
- A stale/unknown market feed must **fail closed** for automated execution.
- Production credential leakage to dev/test/uat is a **security incident**.
