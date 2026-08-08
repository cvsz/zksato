# GitHub repository and Actions configuration

This document is the operational contract for GitHub Actions, pull-request policy, dependency maintenance, security automation, release assurance, UAT evidence, disaster-recovery drills, and production-readiness evidence.

## Workflow inventory

| Workflow | Trigger | Purpose | Baseline requirement |
| --- | --- | --- | --- |
| `CI` | push `main`, PR, merge group, manual | PostgreSQL/Redis integration, migrations, Ruff, branch coverage, Python 3.11-3.14 | required |
| `Quality` | push `main`, PR, merge group, manual | Ruff format, mypy, YAML/actionlint/zizmor, OpenAPI contract, package metadata, runtime-license policy | required |
| `Governance` | push `main`, PR, merge group, manual | required docs, port invariant, immutable action pins, least privilege, ShellCheck, Hadolint | required |
| `Security` | push `main`, PR, merge group, weekly, manual | runtime `pip-audit`, Bandit, Gitleaks, high-confidence secret patterns, optional CodeQL | required for Python security |
| `Container` | relevant push/PR, merge group, manual | production image build, non-root and hardened read-only runtime `/health` smoke | required for runtime/container changes |
| `Container Security` | relevant push/PR, merge group, weekly, manual | Trivy CVE evidence, fixed-critical gate, image CycloneDX SBOM, hardened-runtime check | required for runtime/container changes |
| `PR Policy` | PR | Conventional title plus evidence sections for risk-sensitive changes | required for PRs |
| `Labeler` | PR | path-based labels using an unprivileged `pull_request` trigger | advisory |
| `Resilience` | sensitive PR paths, merge group, weekly, manual | deterministic recovery/fail-closed suite across two hash seeds | required for sensitive changes |
| `Dependency Review` | PR | GitHub dependency review when the private-repository capability is enabled | capability-gated |
| `Repository Health` | GitHub-config push, weekly, manual | read-only GitHub API capability/control evidence | evidence |
| `Performance` | weekly, manual | bounded local hardened-container load probe with explicit p95/failure threshold | evidence |
| `Disaster Recovery Drill` | monthly, manual | migrations, backup, checksum, corruption detection, restore, sentinel verification, timing evidence | evidence |
| `UAT Certification` | manual | protected non-mutating evidence collection against deployed Settrade UAT | protected manual |
| `Production Readiness` | manual | protected non-executing runtime/external evidence gate and one-order manual canary plan | protected manual |
| `Release` | `v*` tag | audited Python release + image scan/SBOM + multi-arch GHCR publication + checksums + optional attestation + GitHub Release | release gate |
| `Release Verification` | published release, manual | re-download/checksum/clean-install and immutable GHCR digest runtime verification | post-release evidence |

GitHub also creates dynamic Dependabot Update and Dependency Graph workflows outside `.github/workflows/`.

## Action supply-chain policy

Every external `uses:` reference must be pinned to a full 40-character commit SHA. Human-readable release versions remain comments only. `Governance` rejects shortened/moving refs, `write-all`, and `pull_request_target` by default. `Quality` independently runs `actionlint` and `zizmor` so workflow syntax and high-confidence workflow-security findings are validated before merge.

Dependabot maintains `pip`, `github-actions`, and Docker ecosystems on a weekly Bangkok-time schedule. Updates are grouped and automatically rebased.

## Recommended protection for `main`

When the repository plan supports rulesets/branch protection, require PRs, stale-approval dismissal, conversation resolution, block force push/deletion, restrict bypass, and require the stable checks that run for every relevant change:

- `CI / Quality / Python 3.11`
- `CI / Compatibility / Python 3.11`
- `CI / Compatibility / Python 3.12`
- `CI / Compatibility / Python 3.13`
- `CI / Compatibility / Python 3.14`
- `Quality / Format, types, workflows, contract, package and licenses`
- `Governance / required-docs`
- `Security / Python dependency and static security`
- `PR Policy / Title and risk-sensitive change policy`

After merge queue is available, the core workflows already support `merge_group`. Do not make path-filtered/capability-gated checks globally required unless their trigger guarantees they run on every protected PR.

## Repository variables and protected environments

Capability-gated repository variables:

- `ENABLE_CODEQL=true` — enable only when code scanning is available for this private repository.
- `ENABLE_DEPENDENCY_REVIEW=true` — enable only when Dependency Review is available.
- `ENABLE_ATTESTATIONS=true` — enable only when private-repository artifact attestations are available.

Create protected environments outside source control:

### `uat`
- required reviewers
- deployment restrictions
- `ZKSATO_UAT_API_KEY`

### `production`
- required reviewers
- deployment restrictions
- `ZKSATO_PRODUCTION_RISK_API_KEY`

Environment secrets must never be repository variables, workflow inputs, committed files, or PR secrets.

## CI and quality guarantees

`CI` uses PostgreSQL 16 and Redis 7, applies all numbered migrations, runs dependency consistency, Ruff, the normal pytest suite with branch coverage, Compose validation, and a Python 3.11-3.14 compatibility matrix. The current branch-coverage floor is 65%; it is a ratchet rather than a target.

`Quality` validates full-repository Ruff formatting, mypy across `src/zksato` and `scripts`, YAML, GitHub Actions semantics, high-confidence workflow security, the safety-critical OpenAPI contract, wheel/sdist build, `twine` metadata, and runtime dependency license policy.

## Security automation

`Security` separately installs runtime dependencies, captures their resolved graph, audits that graph with `pip-audit`, runs Bandit, runs Gitleaks against the tracked tree, and applies a second high-confidence secret-pattern scan. CodeQL remains present but fail-safe/capability-gated.

GitHub-native Secret Protection, push protection, Code Security, private vulnerability reporting, and Dependency Review should be enabled in repository settings when the account/plan supports them. Workflow scanners complement those controls; they do not replace them.

## Container assurance

The Dockerfile is multi-stage and produces a minimal non-root runtime. Container workflows verify user `zksato`, read-only root filesystem compatibility, tmpfs `/tmp`, dropped Linux capabilities, `no-new-privileges`, and `/health`. `Container Security` records HIGH/CRITICAL Trivy findings, blocks fixed CRITICAL vulnerabilities, and emits an image CycloneDX SBOM.

Compose applies the same defensive runtime profile to the API and keeps PostgreSQL/Redis persistent state outside the read-only application filesystem.

## Release process

A release tag must match `pyproject.toml`, e.g. version `0.4.0` requires tag `v0.4.0`. The release workflow:

1. audits resolved runtime dependencies;
2. builds wheel and source distribution;
3. validates metadata and clean installation/version identity;
4. creates dependency and image SBOMs;
5. scans the local release-candidate image before publishing;
6. publishes `linux/amd64` and `linux/arm64` images to GHCR with provenance/SBOM metadata;
7. records the immutable image digest;
8. creates SHA-256 checksums;
9. optionally creates GitHub attestations when supported;
10. creates the GitHub Release.

`Release Verification` then downloads the published assets, checks hashes, installs the wheel in a clean environment, pulls the immutable GHCR digest, and starts it with the hardened runtime profile before accepting `/health`.

The release process intentionally does not deploy production infrastructure or submit broker orders.

## UAT, performance, DR, and readiness evidence

`UAT Certification` is manual, protected, HTTPS-only, and non-mutating. `Performance` targets only a locally built hardened container and emits p50/p95/p99/throughput/failure evidence against explicit limits. `Disaster Recovery Drill` uses ephemeral PostgreSQL, proves checksum corruption detection, restores a checksummed backup, verifies application tables/sentinel data, and records backup/restore durations.

`Production Readiness` never submits an order. It requires production/live runtime selection, durable services, authentication, trusted hosts, four-eyes confirmation, explicit account allow-list, strict reference/session controls, Settrade configuration, clear kill switch, reconciliation, audit integrity, and explicit external evidence for broker/legal/UAT/TLS/secrets/DR/monitoring/incident/rollback/capacity/time-sync/market-data-failover/data-retention/release verification/manual canary authorization. Even when it passes, the generated canary plan remains non-autonomous and limited to one separately authorized order.

## Repository features and plan boundaries

Enable where available:

- Dependabot alerts and security updates;
- secret scanning and push protection;
- CodeQL/Code Security;
- Dependency Review;
- private vulnerability reporting;
- protected `uat` and `production` environments;
- least-privilege Actions token policy;
- branch protection/rulesets and merge queue;
- artifact attestations.

A GitHub API 403 or plan limitation is recorded by `Repository Health` as unavailable capability evidence. Source code must not reinterpret such an external limitation as configured or complete.
