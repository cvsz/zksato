# Operator handoff: external gates

This document is the single entry point for completing the remaining v1.0.0 external gates. Source code cannot close these gates; they require operator, broker, legal, or platform action.

## Gate summary

| Gate | Owner | Evidence artifact | Blocking? |
| --- | --- | --- | --- |
| TFEX broker UAT certification | Operator + broker | `docs/templates/UAT-EVIDENCE.md` | Yes for TFEX live mutation |
| Production alert/RPO/RTO restore evidence | Operator | `docs/templates/PRODUCTION-READINESS-EVIDENCE.md` | Yes for production |
| GitHub protected environments/rulesets/merge queue | GitHub admin | `docs/GITHUB-ENVIRONMENTS.md` | No for localhost; yes for GitHub-delivered releases |
| Broker/legal/TLS/secrets/monitoring/backup authorization | Operator + legal | `docs/templates/PRODUCTION-READINESS-EVIDENCE.md` | Yes for production |
| Manual live canary plan | Operator | `docs/PRODUCTION-READINESS.md` | Yes for live equity mutation |

## Required operator actions

### 1. Settrade TFEX UAT certification
- Install Settrade v2 SDK in UAT environment (`pip install zksato[settrade]`)
- Configure sandbox credentials in `/run/secrets` or vault
- Run `python scripts/uat_certify.py` against local API
- Execute all cases in `docs/templates/UAT-EVIDENCE.md`
- Archive evidence with SDK version, account reference, operator initials, and timestamps
- Record result in `docs/UAT-CERTIFICATION.md`

### 2. Production platform hardening
- Enable TLS with valid certificate chain; verify HSTS and trusted hosts
- Rotate all secrets (`ZKSATO_SESSION_SECRET`, API keys, broker credentials)
- Load secrets from `/run/secrets` or KMS-backed vault; confirm rotation schedule
- Enable PostgreSQL WAL archiving and verify Redis append-only persistence
- Deploy Prometheus + alert delivery; confirm structured JSON logs and optional OTel pipeline

### 3. Backup/restore drill and evidence
- Execute `scripts/backup_postgres.sh` and record checksum
- Restore into isolated target with `CONFIRM_RESTORE=<target> scripts/restore_postgres.sh`
- Measure RPO and RTO; record in `docs/templates/PRODUCTION-READINESS-EVIDENCE.md`
- Run quarterly DR drill using `docs/DR-RUNBOOK.md`

### 4. Verified reference data and calendar
- Load target-period SET/TFEX exchange calendar with holidays and special sessions
- Validate sector metadata, tick-size table, and price-band rules
- Populate `ZKSATO_EQUITY_HOLIDAYS`, `ZKSATO_EQUITY_SPECIAL_SESSIONS_JSON`, and TFEX equivalents
- Record source and verification date

### 5. GitHub repository hardening
- Enable CodeQL, Dependency Review, Secret Protection, and required status checks
- Configure protected environments, rulesets, and merge queue as plan permits
- Document settings in `docs/GITHUB-ENVIRONMENTS.md`

### 6. Broker/legal authorization and canary
- Obtain explicit broker permission for live equity mutation
- Obtain legal/operational sign-off
- Prepare minimal one-order canary plan via `POST /v1/production/canary-plan`
- Execute canary only with four-eyes approval and kill-switch standby
- Reconcile broker order/fill/position state immediately after execution

## Verification endpoints

- `GET /health` — process health
- `GET /livez` — liveness with persistence/coordination/reconciliation/audit checks
- `GET /readyz` — readiness including external gate state
- `POST /v1/production/readiness` — machine-readable readiness report
- `POST /v1/production/canary-plan` — non-executing canary plan generator

## Non-negotiables

- `paper` is the default mode.
- Autonomous live-money execution is forbidden.
- Live orders require explicit operator authorization at the trusted server boundary.
- No LLM, agent, browser state, strategy, or dashboard control may bypass `RiskEngine` or `TradingService`.
- TFEX mutation remains UAT-only until separately certified.
