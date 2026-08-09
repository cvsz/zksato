# Production readiness evidence

## Release identity
Commit/tag, package/image digest, checksums/SBOM, verification run.

## Platform
- [ ] TLS
- [ ] auth/RBAC/session secret
- [ ] managed secrets/rotation
- [ ] PostgreSQL/Redis
- [ ] monitoring/alerts/logs/traces
- [ ] backup/restore drill
- [ ] capacity/SLO/time sync
- [ ] incident/rollback/on-call

## Trading
- [ ] broker production permission
- [ ] account allow-list
- [ ] verified exchange calendar/reference data
- [ ] required UAT lifecycle evidence
- [ ] fresh reconciliation/no unresolved state
- [ ] kill switch
- [ ] one-time operator approval/four-eyes policy
- [ ] TFEX separately blocked/certified

## Approval
Legal/operational and explicit minimal manual canary authorization.

`autonomous_execution` must remain false.
