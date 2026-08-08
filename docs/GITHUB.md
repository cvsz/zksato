# GitHub repository configuration

## Recommended branch protection for `main`
Require pull request, at least one approval for sensitive changes, dismiss stale approvals, require conversation resolution, require `CI` and `Governance` checks, block force pushes/deletion, restrict bypass.

## Repository features
Enable Dependabot alerts/updates, secret scanning/push protection where available, code scanning if configured, vulnerability reporting, Actions with least-privilege tokens.

## Labels
Suggested: `bug`, `enhancement`, `documentation`, `security`, `risk`, `strategy`, `market-data`, `broker`, `tfex`, `persistence`, `dashboard`, `operations`, `incident`, `needs-design`, `P0`, `P1`, `P2`, `P3`.

## Templates
Issue templates cover bugs, features, strategy/risk changes, incidents. PR template requires risk/testing/rollout/rollback/security evidence.

## Releases
Use `.github/release.yml` categories and `CHANGELOG.md`. Attach migration/UAT notes for sensitive releases.
