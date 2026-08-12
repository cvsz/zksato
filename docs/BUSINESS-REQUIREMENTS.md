# Business requirements

## Objective
Provide a controlled platform for SET/TFEX market research, paper execution, broker UAT, deterministic risk enforcement, reconciliation, and operator evidence without granting autonomous unrestricted live-money authority.

## Outcomes
- reduce manual repetition in research and paper/UAT workflows;
- make execution decisions deterministic, auditable, reproducible, and reviewable;
- maintain durable evidence for orders, fills, risk decisions, account snapshots, strategy runs, and operations;
- surface system health and production-readiness gaps to operators;
- support controlled evolution through CI/CD, migrations, ADRs, runbooks, and rollback procedures.

## Stakeholders
Repository owner/maintainers, strategy operators, order approvers, risk administrators, auditors, platform operators, and broker/UAT counterparts.

## Constraints
- broker/exchange/legal authorization is external to the repository;
- production calendars/reference data require verified operator-provided sources;
- paper/backtest simulation must not be represented as exchange microstructure truth;
- external evidence is required before any production readiness claim.

## Success measures
Correctness and safety take precedence over trade frequency. Success is measured through deterministic tests, reconciliation convergence, durable evidence integrity, bounded operational recovery, source assurance, and successful externally witnessed UAT/DR/readiness gates.
