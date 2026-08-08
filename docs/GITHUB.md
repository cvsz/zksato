# GitHub repository and Actions configuration

zksato treats GitHub Actions as a verification and release control plane. Workflows must remain least-privilege, fail closed on correctness checks, and must never gain a path to autonomous live-money execution.

## Workflow inventory

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `CI` | PR, push to `main`, manual | Quality checks, Python 3.11/3.12 PostgreSQL+Redis integration tests, migrations, Compose validation, container build and health smoke test |
| `Governance` | PR, push to `main`, manual | Required project documents, canonical port `9569`, workflow safety policy, shell syntax |
| `Security` | PR, push to `main`, weekly, manual | `pip-audit`, Trivy repository/secret/misconfiguration scan, Trivy container scan |
| `Nightly` | daily, manual | Real runtime health/load probe plus PostgreSQL backup/restore drill on disposable CI data |
| `Release` | `v*` tag, manual no-op unless tag ref | Build Python wheel/sdist, validate tag/version, publish provenance/SBOM-enabled container to GHCR, create GitHub Release |
| `Settrade UAT Certification` | manual only | Read-only probe of a deployed sandbox/UAT endpoint; never submits an order |
| `Production Readiness` | manual only | Evaluate externally supplied evidence and generate a non-executing canary plan |

Third-party and GitHub-maintained actions are pinned to immutable commit SHAs with version comments. Dependabot tracks GitHub Actions, Python dependencies, and Docker images so pins can be reviewed and updated through pull requests.

## Recommended branch protection for `main`

Require pull requests, conversation resolution, and reviewed changes for sensitive paths. Require successful checks from `CI`, `Governance`, and `Security` before merge. Block force pushes and branch deletion and restrict bypass privileges.

For high-risk changes under `src/zksato/risk.py`, `src/zksato/service.py`, `src/zksato/broker/`, TFEX execution code, security policy, migrations, and `.github/workflows/`, honor `CODEOWNERS` and require an explicit review.

## Actions permissions

Workflows declare top-level permissions explicitly. Verification workflows use `contents: read`. The release workflow is the only normal workflow granted `contents: write` and `packages: write`, solely for GitHub Releases and GHCR publication.

Do not introduce `pull_request_target` or `permissions: write-all`. Do not expose repository/environment secrets to untrusted pull-request code.

## Environments and secrets

The following are external GitHub settings and cannot be created or certified by repository source alone:

- Environment `uat`
  - secret `ZKSATO_UAT_API_KEY`: read-capable API key for the deployed UAT zksato control plane
  - recommended required reviewer before workflow execution
- Environment `production`
  - secret `ZKSATO_PRODUCTION_READ_API_KEY`: read/readiness-only API key; it must not carry order-execution authority
  - required reviewers and deployment protection rules strongly recommended

Broker App ID/App Secret/PIN values do not belong in GitHub workflow YAML and should not be added as repository secrets merely to make CI pass. Broker credentials belong in the deployed secret-management boundary described in `docs/SECRETS-RUNBOOK.md`.

## Dependency automation

`.github/dependabot.yml` covers:

- Python runtime/development dependencies
- GitHub Actions
- Docker base images

Updates are grouped and scheduled in the `Asia/Bangkok` timezone. Every dependency PR must pass the same CI, governance, and security gates as application changes.

## Release process

1. Ensure `pyproject.toml` contains the intended version.
2. Merge all release changes with green CI/security/governance checks.
3. Create and push tag `v<project.version>`.
4. `Release` verifies tag/version equality, builds wheel and sdist, runs `twine check`, builds the container, and publishes:
   - Python distribution files as GitHub Release assets
   - `ghcr.io/cvsz/zksato:<tag>`
   - `ghcr.io/cvsz/zksato:latest`
   - BuildKit provenance and SBOM metadata
5. Record migrations, UAT evidence, rollback considerations, and operator-facing changes in the release notes.

A release artifact does not by itself authorize production brokerage execution.

## Scheduled verification

`Nightly` starts zksato against disposable PostgreSQL and Redis services, applies every migration, runs a bounded HTTP load probe on `/health`, then independently validates backup/checksum/restore behavior into a fresh database. All data is synthetic CI data.

`Security` runs weekly in addition to PR and `main` events. Vulnerability findings should be remediated or explicitly reviewed rather than suppressed globally.

## Repository features to enable in GitHub settings

Enable Dependabot alerts and updates, secret scanning/push protection where the repository plan supports them, private vulnerability reporting if applicable, and GitHub Actions with the minimum token permissions necessary. Code scanning/Advanced Security may be enabled separately when available; the repository security workflow does not depend on those paid/private-repository features.

## Labels and templates

Suggested labels: `bug`, `enhancement`, `documentation`, `security`, `risk`, `strategy`, `market-data`, `broker`, `tfex`, `persistence`, `dashboard`, `operations`, `incident`, `needs-design`, `P0`, `P1`, `P2`, `P3`.

Issue templates cover bugs, features, strategy/risk changes, and incidents. The PR template requires risk, testing, rollout, rollback, and security evidence.
