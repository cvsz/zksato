# Change management

## Change classes
- Standard: docs, low-risk tests/tooling with no runtime authority impact.
- Normal: product/runtime change requiring normal review and CI.
- High risk: risk, execution, broker, auth, portfolio/P&L, migrations, TFEX, production workflow, secrets.
- Emergency: bounded hotfix for an active incident.

## Required record
Every non-trivial PR states reason, scope, risk/execution impact, validation, data/migrations, observability, rollout, rollback, and documentation. High-risk changes also reference an issue/change record and security/risk evidence.

## Approval
Repository merge approval is separate from broker/UAT/production authorization. Environment promotion requires its own evidence and operator approval.

## Emergency change
Minimize scope, preserve auditability, avoid bypassing core safety gates, record temporary deviations, and schedule follow-up remediation/postmortem.
