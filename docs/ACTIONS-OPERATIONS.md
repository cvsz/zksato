# GitHub Actions operations

This runbook covers the source-controlled assurance workflows and the external GitHub settings required to turn them into an end-to-end protected delivery system.

## Required baseline checks

Before merging a non-trivial PR, require all applicable source-controlled checks to be green:

- CI: PostgreSQL/Redis integration, migrations, Ruff, pytest branch coverage, Python 3.11-3.14.
- Quality: format, mypy, YAML/actionlint/zizmor, OpenAPI safety contract, package and runtime-license policy.
- Security: runtime `pip-audit`, Bandit, Gitleaks, high-confidence secret scan.
- Governance: docs/port invariants, immutable action pins, least privilege, ShellCheck, Hadolint.
- Container and Container Security for runtime/image changes.
- Resilience for risk/reconciliation/persistence/approval/auth changes.
- PR Policy for title/evidence requirements.

CodeQL and Dependency Review may be skipped when the private-repository plan does not expose those APIs. Do not convert plan-dependent checks into required status checks until their availability is stable.

## Evidence workflows

### Performance
Runs only against a locally built hardened container. Default bounded evidence is 1,000 requests, concurrency 25, zero tolerated failures, and p95 <= 500 ms. Inputs remain capped in `scripts/load_test.py`.

### Disaster Recovery Drill
The monthly/manual job applies all migrations to ephemeral PostgreSQL, seeds a sentinel, creates a custom-format backup, verifies its checksum, proves a deliberately modified copy does not match the checksum, restores the real backup, verifies public tables and sentinel data, and emits measured backup/restore timings.

This proves the repository procedure. A production restore drill and measured production RPO/RTO remain external operational evidence.

### Repository Health
Performs read-only GitHub API probes for repository metadata, Actions permissions, active workflows, environments, main protection, rulesets, code scanning, secret scanning, and Dependabot alerts. Unsupported or forbidden APIs are recorded rather than guessed.

### UAT Certification
Requires the protected `uat` environment and `ZKSATO_UAT_API_KEY`. The probe is non-mutating and requires the deployed application to report sandbox mode and complete Settrade configuration.

### Production Readiness
Requires the protected `production` environment and `ZKSATO_PRODUCTION_RISK_API_KEY`. The workflow only POSTs evidence to `/v1/production/readiness` and `/v1/production/canary-plan`; it never calls an order endpoint. An accepted plan must remain `autonomous_execution=false` and `maximum_orders=1`.

## Release container flow

A `v*` tag that exactly matches `pyproject.toml` creates Python distributions and a multi-architecture GHCR image. The release candidate is scanned before publication. Release assets include dependency SBOM, image SBOM, immutable image digest, and SHA-256 checksums. `Release Verification` independently re-downloads those assets and starts the immutable digest with the hardened runtime profile.

Do not create the tag until normal CI/Quality/Security/Container gates are green on the intended release commit.

## Required external GitHub setup

Source code cannot create or certify the following account/repository controls through the currently connected integration. Configure them in GitHub settings when supported:

1. `uat` environment with required reviewers and `ZKSATO_UAT_API_KEY`.
2. `production` environment with required reviewers and `ZKSATO_PRODUCTION_RISK_API_KEY`.
3. Main-branch ruleset/protection with stable required checks, no force push/deletion, limited bypass, review/conversation requirements.
4. Merge queue after ruleset/plan support is available; core checks already accept `merge_group`.
5. Secret scanning/push protection and private vulnerability reporting when available.
6. Code Security/CodeQL and Dependency Review when available, then set the matching repository variables.
7. Artifact attestations when the private-repository plan supports them, then set `ENABLE_ATTESTATIONS=true`.
8. Least-privilege repository/organization Actions token policy.

## Failure handling

- A CI/Quality/Security failure blocks merge until the root cause is fixed; do not bypass a safety check to make a PR green.
- A Trivy fixed-CRITICAL finding blocks the release/runtime image path.
- A failed DR drill invalidates backup/restore readiness until rerun successfully.
- A failed UAT or production-readiness check never permits fallback to live execution.
- An unavailable plan-gated GitHub feature remains an explicit gap, not a false pass.
- Unknown broker mutation outcomes remain reconciliation problems and are never repaired by blind GitHub Actions retry.
