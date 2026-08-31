# Production readiness evidence

## Release identity
- Commit SHA/tag:
- Container/image digest:
- SBOM/checksums:
- Verification run:
  - `ruff check .` result:
  - `ruff format --check .` result:
  - `pytest -m "not uat and not performance"` result:
  - `docker compose config` result:
  - `docker compose build` result:

## Platform
- [ ] TLS: certificate chain, expiry, HSTS, trusted hosts verified
- [ ] auth/RBAC/session: API keys rotated, session secret loaded from `/run/secrets`, CSRF enabled
- [ ] managed secrets/rotation: KMS or vault-backed rotation schedule tested
- [ ] PostgreSQL/Redis: durable persistence validated, Redis correctness boundary confirmed
- [ ] monitoring/alerts/logs/traces: Prometheus metrics, structured JSON logs, optional OTel pipeline delivering
- [ ] backup/restore drill: RPO/RTO measured, restore into isolated target verified, checksum validated
- [ ] capacity/SLO/time sync: load probe evidence, NTP sync confirmed, rate limits coordinated
- [ ] incident/rollback/on-call: runbook reviewed, DR drill passed, on-call rotation active

## Trading
- [ ] broker production permission: explicit broker/legal authorization for live equity mutation
- [ ] account allow-list: `ZKSATO_ACCOUNT_ALLOW_LIST` populated, tested
- [ ] verified exchange calendar/reference data: target-period SET/TFEX calendar loaded, holidays/special sessions validated
- [ ] required UAT lifecycle evidence: all UAT cases passed, evidence archived
- [ ] fresh reconciliation/no unresolved state: `reconciliation_ready=true`, zero unresolved orders
- [ ] kill switch: `ZKSATO_KILL_SWITCH=true` tested, automation halted
- [ ] one-time operator approval/four-eyes policy: intent-bound approval flow tested, reviewed by second operator
- [ ] TFEX separately blocked/certified: TFEX mutation remains UAT-only unless separately certified

## Approval
Legal/operational and explicit minimal manual canary authorization.

`autonomous_execution` must remain false.
