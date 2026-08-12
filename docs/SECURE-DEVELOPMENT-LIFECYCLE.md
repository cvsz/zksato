# Secure development lifecycle

## Plan
Classify data, trust boundaries, execution authority, external dependencies, and abuse/failure cases. Use ADR/RFC and threat-model templates for architectural changes.

## Implement
Validate input, authorize server-side, use deterministic risk controls, isolate broker credentials, avoid secret-bearing errors, implement idempotency/reconciliation, and keep paper/UAT/live explicit.

## Verify
Run formatting/types/tests/coverage/OpenAPI/package/dependency/SAST/secret/container/workflow checks as applicable. Add security regression tests for discovered defects.

## Release
Review SBOM/checksums/artifact identity, migrations, rollback, runbooks, unresolved vulnerabilities, and external environment prerequisites.

## Operate
Monitor health/SLO/security events, rotate secrets, rehearse incident/DR response, and feed incident/postmortem lessons back into tests and controls.
