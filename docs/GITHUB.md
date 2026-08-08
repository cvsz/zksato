# GitHub repository and Actions configuration

This document is the operational contract for GitHub Actions, branch protection, dependency maintenance, security automation, releases, UAT evidence, production-readiness evidence, and disaster-recovery drills.

## Workflow inventory

| Workflow | Trigger | Purpose | Required by default |
| --- | --- | --- | --- |
| `CI` | push to `main`, PR, manual | Python 3.11 integration checks plus Python 3.11-3.14 compatibility matrix | yes |
| `Governance` | push to `main`, PR, manual | required docs, port invariant, immutable action pins, least-privilege workflow policy | yes |
| `Security` | push to `main`, PR, weekly, manual | `pip-audit`, Bandit, high-confidence secret patterns, optional CodeQL | yes for `python-security` |
| `Container` | relevant push/PR paths, manual | Docker build, non-root invariant, runtime `/health` smoke test | recommended |
| `Dependency Review` | PR | GitHub dependency review, gated by repository capability | optional/gated |
| `Performance` | weekly, manual | bounded local health-endpoint load probe | evidence workflow |
| `Disaster Recovery Drill` | monthly, manual | PostgreSQL migration → backup → checksum → restore → sentinel verification | evidence workflow |
| `UAT Certification` | manual | non-mutating evidence collection against protected Settrade UAT deployment | manual approval workflow |
| `Production Readiness` | manual | fail-closed runtime/external readiness evaluation and non-executing canary-plan evidence | manual approval workflow |
| `Release` | `v*` tag | dependency audit, wheel/sdist, SBOM/checksums, GHCR image, optional attestation, GitHub Release | tag gate |

## Action supply-chain policy

All external `uses:` references in `.github/workflows/` must be pinned to a full 40-character commit SHA. Human-readable release versions stay in comments, for example:

```yaml
uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
```

`Governance` rejects moving tags such as `@main`, `@master`, `@v6`, shortened SHAs, and `pull_request_target` by default. Every workflow must declare explicit top-level `permissions`; `write-all` is forbidden.

Dependabot keeps `pip`, `github-actions`, and Docker references current on a weekly Bangkok-time schedule. Updates are grouped to reduce PR noise while preserving reviewability.

## Recommended branch protection for `main`

Require pull requests for non-trivial changes, dismiss stale approvals, require conversation resolution, block force pushes and branch deletion, and restrict bypass. Require the stable checks that always run:

- `CI / Quality / Python 3.11`
- all supported-interpreter `CI / Compatibility` jobs if the repository promises Python 3.11+
- `Governance / required-docs`
- `Security / Python dependency and static security`

Do not require path-filtered or capability-gated checks such as `Container`, `CodeQL`, or `Dependency Review` until their trigger and repository entitlements guarantee that they run for every protected PR.

## Repository variables and protected environments

The workflows intentionally fail closed or skip capability-dependent features instead of assuming a GitHub plan or external environment.

Repository variables:

- `ENABLE_CODEQL=true` — enables CodeQL advanced analysis. Enable only when code scanning is available for this private repository.
- `ENABLE_DEPENDENCY_REVIEW=true` — enables Dependency Review. Enable only when the dependency review API is available for the repository.
- `ENABLE_ATTESTATIONS=true` — enables release artifact attestations. Enable only when private-repository attestations are available for the account/organization plan.

Create a protected GitHub environment named `uat` with required reviewers and the environment secret documented in the UAT runbook. The UAT workflow accepts only an HTTPS deployment URL and performs non-mutating certification probes.

Create a separate protected environment named `production` with required reviewers for the manual Production Readiness workflow. That workflow accepts only an HTTPS endpoint, requires the literal confirmation `READINESS_ONLY`, evaluates the repository-defined external/runtime evidence contract, stores the report and canary plan as short-lived evidence, and never calls an order endpoint. See `ACTIONS-OPERATIONS.md` and `PRODUCTION-READINESS.md`.

## CI guarantees

The primary CI job validates:

1. pinned Python 3.11 environment and cached dependency installation;
2. byte compilation of `src`, tests, and scripts;
3. all numbered PostgreSQL migrations against PostgreSQL 16;
4. Redis service availability during the integration job;
5. `pip check` dependency consistency;
6. Ruff policy;
7. pytest excluding explicit UAT/performance markers;
8. Docker Compose configuration;
9. JUnit evidence retained as a short-lived workflow artifact.

A separate compatibility matrix runs the non-UAT/non-performance test suite on Python 3.11, 3.12, 3.13, and 3.14 because `pyproject.toml` declares `requires-python = ">=3.11"`.

## Security automation

`Security` performs dependency vulnerability auditing with `pip-audit`, Bandit medium/high static analysis, and a high-confidence scan for common committed credential formats. CodeQL is preconfigured but gated behind `ENABLE_CODEQL` so unsupported private-repository entitlements cannot make baseline CI permanently red.

GitHub-native secret scanning and push protection should also be enabled in repository settings whenever available. Workflow scanning complements those controls; it does not replace them.

## Container validation

`Container` builds the production Dockerfile with `--pull`, verifies the configured image user is `zksato`, launches the image on port `9569`, and requires `/health` to become reachable. It does not publish the image or inject broker credentials.

Docker base-image changes are maintained by Dependabot and must pass the same repository controls as application changes.

## Release process

A release tag must match the version in `pyproject.toml`, e.g. project version `0.4.0` requires tag `v0.4.0`.

The release workflow:

1. audits resolved dependencies;
2. builds wheel and source distribution;
3. installs the wheel into a clean virtual environment;
4. generates a CycloneDX JSON dependency SBOM;
5. builds and publishes versioned and `latest` zksato images to GHCR with BuildKit provenance and container SBOM metadata;
6. records the immutable container digest in `CONTAINER_IMAGE.txt` and creates SHA-256 checksums;
7. uploads a retained release bundle;
8. optionally generates GitHub artifact attestations;
9. creates the GitHub Release from the tag.

It intentionally does not publish to PyPI or deploy production infrastructure. Publishing a release container is artifact distribution, not permission to connect it to a brokerage account.

## UAT, production-readiness, performance, and disaster-recovery evidence

`UAT Certification` is manual and uses a protected environment. It runs `scripts/uat_certify.py` against a deployed HTTPS endpoint and stores non-mutating evidence.

`Production Readiness` is manual and uses a separate protected environment. It only calls the non-executing readiness/canary-plan boundary and fails closed unless the application confirms the manual-canary prerequisites. Source code and Actions cannot self-certify external broker, legal, TLS, monitoring, or operator approval.

`Performance` is bounded by the existing load-probe caps and targets only a locally built container. It cannot be used by the scheduled workflow to load-test an external production endpoint.

`Disaster Recovery Drill` uses an ephemeral PostgreSQL database, applies every migration, writes a sentinel, creates a checksummed custom-format backup, restores it with the repository restore guard, and verifies the sentinel after restore. Production restore drills remain an operator-controlled exercise documented in `docs/DR-RUNBOOK.md`.

## Repository features

Enable where available:

- Dependabot alerts and security updates;
- secret scanning and push protection;
- code scanning / CodeQL after setting `ENABLE_CODEQL=true`;
- dependency review after setting `ENABLE_DEPENDENCY_REVIEW=true`;
- private vulnerability reporting where applicable;
- protected `uat` and `production` environments with required reviewers;
- least-privilege Actions token policy;
- branch protection or rulesets for `main` and release tags;
- GHCR package visibility and retention policy appropriate for this private repository.

## Labels and templates

Suggested labels: `bug`, `enhancement`, `documentation`, `security`, `risk`, `strategy`, `market-data`, `broker`, `tfex`, `persistence`, `dashboard`, `operations`, `incident`, `needs-design`, `P0`, `P1`, `P2`, `P3`.

Issue templates cover bugs, features, strategy/risk changes, and incidents. The PR template requires risk, testing, rollout, rollback, and security evidence.
