# Maintainers

## Current ownership
Repository owner and default maintainer: `@cvsz`.

`CODEOWNERS` is authoritative for path-level review routing. This file describes responsibilities, not GitHub permission state.

## Maintainer responsibilities
- preserve the risk/execution trust boundary in `AGENTS.md` and `SECURITY.md`;
- review high-risk changes to risk, execution, broker adapters, auth, migrations, portfolio accounting, TFEX, and CI/CD;
- keep documentation, ADRs, runbooks, API contracts, migrations, and feature status synchronized with code;
- require rollout/rollback plans for non-trivial operational changes;
- refuse claims of production/UAT completion without external evidence;
- protect secrets and avoid using production credentials in pull-request workflows.

## Release authority
A maintainer may prepare a release only after required source-controlled checks pass. Production promotion additionally requires environment-specific authorization and evidence described in `docs/PRODUCTION-READINESS.md`.

## Succession
When ownership expands, update this file, `.github/CODEOWNERS`, `GOVERNANCE.md`, and GitHub repository roles in the same governance change.
