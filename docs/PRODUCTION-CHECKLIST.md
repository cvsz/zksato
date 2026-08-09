# Production checklist

This checklist does not authorize trading; it records prerequisites for a separately approved manual canary.

## Source/release
- [ ] final revision checks green
- [ ] release artifact/digest/checksum verified
- [ ] SBOM/security findings reviewed
- [ ] migrations and rollback reviewed

## Platform
- [ ] TLS/ingress verified
- [ ] auth/RBAC/session signing configured
- [ ] managed secrets and rotation verified
- [ ] PostgreSQL/Redis health and backups verified
- [ ] monitoring/alerts/log/trace delivery verified
- [ ] capacity/SLO/time-sync evidence reviewed

## Trading
- [ ] broker production permission confirmed
- [ ] account allow-list confirmed
- [ ] target-period exchange calendar/reference data verified
- [ ] Settrade equity UAT certified for required lifecycle cases
- [ ] TFEX remains blocked unless separately certified
- [ ] reconciliation fresh with no unresolved state
- [ ] kill switch/operator procedure tested
- [ ] one-time approval/four-eyes policy verified

## Operations
- [ ] DR restore drill evidence current
- [ ] incident/rollback/on-call contacts current
- [ ] legal/operational approval recorded
- [ ] minimal manual canary explicitly authorized

Autonomous execution must remain `false`.
