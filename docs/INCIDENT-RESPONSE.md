# Incident response

## Severity
- SEV-1: potential uncontrolled live monetary impact/security compromise.
- SEV-2: material trading outage or uncertain broker/local state.
- SEV-3: degraded feature with workaround.
- SEV-4: minor/non-urgent defect.

## Immediate actions
Stop automation/new submissions, check broker open orders/positions directly, preserve logs/audit/config/version/timestamps, rotate compromised credentials if suspected, declare incident owner and timeline.

## Recovery gate
Broker/local state reconciled, root trigger contained, risk/authorization controls verified, feed healthy, rollback/fix validated, operator explicitly approves resume.

## Postmortem
Impact, timeline, detection, root cause, contributing factors, what worked/failed, corrective actions with owners/dates, regression tests, documentation/runbook changes.
