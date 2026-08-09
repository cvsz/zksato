# GitHub Actions operations

This runbook covers the source-controlled assurance workflows and the external GitHub settings required to turn them into an end-to-end protected delivery system.

The desired GitHub Environment configuration is source-controlled in `.github/environments/requirements.json`. Use `scripts/github_environment_admin.py` and `docs/GITHUB-ENVIRONMENTS.md` to audit/bootstrap non-secret settings and install secret values through an approved secure path.

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
The monthly/manual job applies all migrations to ephemeral PostgreSQL, seeds a sentinel, creates a custom-format backup, verifies its checksum, proves a deliberately modified copy does not match the checksum, restores the real backup, verifies public tables/sentinel data, and emits measured backup/restore timings.

This proves the repository procedure. A production restore drill and measured production RPO/RTO remain external operational evidence.

### Repository Health
Performs read-only GitHub API probes for repository metadata, Actions permissions, active workflows, environments, main protection, rulesets, code scanning, secret scanning, and Dependabot alerts. When the environment API is readable, missing environments declared in `.github/environments/requirements.json` are blocking findings. Unsupported or forbidden APIs are recorded rather than guessed.

### UAT Certification
Requires the `uat` environment, `ZKSATO_UAT_API_KEY`, and `ZKSATO_UAT_BASE_URL` unless a manual HTTPS URL override is supplied. The job uses the environment without creating deployment-history records. The probe is non-mutating and requires the deployed application to report sandbox mode and complete Settrade configuration.

### Production Readiness
Requires the `production` environment, `ZKSATO_PRODUCTION_RISK_API_KEY`, and `ZKSATO_PRODUCTION_BASE_URL` unless a manual HTTPS URL override is supplied. The job uses the environment without creating deployment-history records. It only POSTs evidence to `/v1/production/readiness` and `/v1/production/canary-plan`; it never calls an order endpoint. An accepted plan must remain `autonomous_execution=false` and `maximum_orders=1`.

## Release container flow

A `v*` tag that exactly matches `pyproject.toml` runs through the `release` GitHub Environment and creates Python distributions plus a multi-architecture GHCR image. The release candidate is scanned before publication. Release assets include dependency SBOM, image SBOM, immutable image digest, and SHA-256 checksums. `Release Verification` independently re-downloads those assets and starts the immutable digest with the hardened runtime profile.

Do not create the tag until normal CI/Quality/Security/Container gates are green on the intended release commit.

## Required external GitHub setup

The source-controlled contract defines the expected settings but the currently connected GitHub integration cannot write Environment settings/secrets/variables. Apply them from a trusted administrator path using `docs/GITHUB-ENVIRONMENTS.md`.

1. Create `uat`; restrict it to branch `main`; install `ZKSATO_UAT_BASE_URL` and secret `ZKSATO_UAT_API_KEY`.
2. Create `production`; restrict it to branch `main`; install `ZKSATO_PRODUCTION_BASE_URL` and secret `ZKSATO_PRODUCTION_RISK_API_KEY`.
3. Create `release`; restrict it to tag `v*`; keep `ENABLE_ATTESTATIONS=false` until that capability is verified.
4. Add required reviewers/prevent-self-review where the private-repository GitHub plan exposes those controls.
5. Configure a main-branch ruleset/protection with stable required checks, no force push/deletion, limited bypass, and review/conversation requirements.
6. Enable merge queue after ruleset/plan support is available; core checks already accept `merge_group`.
7. Enable secret scanning/push protection and private vulnerability reporting when available.
8. Enable Code Security/CodeQL and Dependency Review when available, then set the matching repository variables.
9. Enable artifact attestations when supported, then set `ENABLE_ATTESTATIONS=true` only after verification.
10. Maintain least-privilege repository/organization Actions token policy.

Do not copy Settrade App Secret/PIN, database/Redis credentials, session keys, application API-key registries, live confirmation tokens, or webhook targets into GitHub Actions unless a separately reviewed deployment workflow actually requires them. Those are runtime secret-manager concerns.

## Failure handling

- A CI/Quality/Security failure blocks merge until the root cause is fixed; do not bypass a safety check to make a PR green.
- A Trivy fixed-CRITICAL finding blocks the release/runtime image path.
- A failed DR drill invalidates backup/restore readiness until rerun successfully.
- A failed UAT or production-readiness check never permits fallback to live execution.
- An unavailable plan-gated GitHub feature remains an explicit gap, not a false pass.
- Missing required GitHub Environments remain a configuration blocker until they are created and audited.
- Unknown broker mutation outcomes remain reconciliation problems and are never repaired by blind GitHub Actions retry.
