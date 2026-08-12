# GitHub environments and configuration contract

This runbook defines the GitHub-side configuration required by zksato. The machine-readable source of truth is `.github/environments/requirements.json` and the audit/bootstrap implementation is `scripts/github_environment_admin.py`.

## Design principles

- GitHub Environments gate **GitHub workflow access**, not trading authority.
- Broker mutation remains controlled by zksato `TradingService`, deterministic `RiskEngine`, reconciliation, and explicit operator authorization.
- No environment configuration may create autonomous live-money execution.
- TFEX production mutation remains unavailable.
- GitHub Actions should hold only credentials that the workflow itself needs. Broker App Secret, PIN, database credentials, session secrets, runtime API keys, and notification endpoints belong in the deployment/runtime secret manager, not in GitHub just because they are secrets.
- Environment names, branch/tag policy, required secret names, required variable names, and non-sensitive managed defaults are source-controlled. Secret **values** are never committed.

## Required environments

| Environment | Workflow | Deployment record | Allowed ref | Required secret | Required variable |
| --- | --- | --- | --- | --- | --- |
| `uat` | `UAT Certification` | no | branch `main` | `ZKSATO_UAT_API_KEY` | `ZKSATO_UAT_BASE_URL` |
| `production` | `Production Readiness` | no | branch `main` | `ZKSATO_PRODUCTION_RISK_API_KEY` | `ZKSATO_PRODUCTION_BASE_URL` |
| `release` | `Release` | yes | tag `v*` | none | none |

`release` manages `ENABLE_ATTESTATIONS=false` as a safe default. Repository-level capability flags `ENABLE_CODEQL`, `ENABLE_DEPENDENCY_REVIEW`, and `ENABLE_ATTESTATIONS` also default to `false` until the corresponding GitHub feature is verified for this private repository.

## Why UAT and production use `deployment: false`

The UAT certification and production-readiness jobs are evidence/check jobs, not deployments. They still reference a GitHub Environment and therefore still receive its secrets/variables and protection rules, but they do not create misleading deployment-history records.

The release job publishes artifacts and a GHCR image, so it uses a normal deployment-tracked `release` environment.

## Bootstrap non-secret environment configuration

The bootstrap tool uses the GitHub REST API and does not print secret values.

Required token capabilities for applying environment configuration:

- repository **Administration: write** for creating/updating environments and deployment branch/tag policies;
- repository **Environments: read/write** for environment variables/secrets inventory;
- repository Actions variables permission if repository capability flags are managed by API.

Run from a trusted workstation, never from an untrusted PR:

```bash
export GH_TOKEN='<fine-grained-admin-token>'
python scripts/github_environment_admin.py apply \
  --repository cvsz/zksato \
  --token-env GH_TOKEN \
  --output github-environments.json
```

The command is idempotent for environment existence, expected branch/tag policies, and managed non-sensitive defaults. It does **not** prune unknown policies and does not invent secret values.

### Optional required reviewer

When the GitHub plan supports required reviewers for this private repository, add a reviewer while applying:

```bash
python scripts/github_environment_admin.py apply \
  --repository cvsz/zksato \
  --token-env GH_TOKEN \
  --reviewer SECOND_OPERATOR
```

The tool enables `prevent_self_review` when a reviewer is supplied. Do not configure the workflow initiator as the only meaningful second-person control. Required reviewers/wait timers are plan-gated for private repositories on some GitHub plans; the audit reports the absence as a warning rather than pretending the control exists.

## Install required environment variables

Environment URLs are non-secret and should be stored as GitHub Environment variables so manual workflow dispatch does not require repeatedly typing them.

```bash
gh variable set ZKSATO_UAT_BASE_URL \
  --env uat \
  --body 'https://YOUR-UAT-HOST'

gh variable set ZKSATO_PRODUCTION_BASE_URL \
  --env production \
  --body 'https://YOUR-PRODUCTION-HOST'
```

The workflows still allow an explicit `base_url` dispatch input as an operator override. Both workflows reject non-HTTPS endpoints; production readiness additionally rejects credentials, query strings, fragments, loopback, unspecified, and link-local addresses.

## Install required environment secrets

Use interactive stdin, a secret manager, or an approved secure automation path. Do not put values on a command line that is retained in shell history.

```bash
gh secret set ZKSATO_UAT_API_KEY --env uat

gh secret set ZKSATO_PRODUCTION_RISK_API_KEY --env production
```

These keys should have only the application permissions required by the corresponding evidence endpoint. They are **not** Settrade App Secret/PIN credentials.

## Runtime secrets that must stay outside GitHub Actions

Unless a future source-reviewed deployment workflow has a demonstrated need, do not install the following as GitHub Environment secrets:

- `ZKSATO_DATABASE_URL`
- `ZKSATO_REDIS_URL`
- `ZKSATO_SETTRADE_APP_ID`
- `ZKSATO_SETTRADE_APP_SECRET`
- `ZKSATO_SETTRADE_BROKER_ID`
- `ZKSATO_SETTRADE_ACCOUNT_NO`
- `ZKSATO_SETTRADE_DERIVATIVES_ACCOUNT_NO`
- `ZKSATO_SETTRADE_PIN`
- `ZKSATO_SESSION_SECRET`
- `ZKSATO_API_KEYS`
- `ZKSATO_LIVE_CONFIRMATION_TOKEN`
- `ZKSATO_NOTIFICATION_WEBHOOK_URL`

The deployed service should receive these through its managed secret system or the supported `ZKSATO_SECRET_DIR` mount.

## Deployment branch/tag restrictions

The contract configures custom deployment policies:

- `uat`: branch `main`
- `production`: branch `main`
- `release`: tag `v*`

These policies are independent of branch protection. Main branch protection/rulesets should still require review and stable CI checks. Release tags should only be created from a fully reviewed commit whose project version matches the tag.

## Audit

Audit without mutating settings:

```bash
export GH_TOKEN='<read-capable-token>'
python scripts/github_environment_admin.py audit \
  --repository cvsz/zksato \
  --token-env GH_TOKEN \
  --output github-environments.json
```

The audit checks:

- required environment existence;
- deployment branch/tag-policy configuration;
- required environment secret **names** only;
- required environment variables;
- managed variable values;
- repository capability-variable defaults where readable;
- required-reviewer presence as a plan-sensitive recommendation.

An API 403 or unavailable plan feature is reported as unknown/unavailable evidence rather than a pass.

## Rotation

For `ZKSATO_UAT_API_KEY` or `ZKSATO_PRODUCTION_RISK_API_KEY`:

1. issue a replacement application key with the minimum role;
2. update the GitHub Environment secret;
3. run the corresponding non-mutating workflow;
4. confirm audit/evidence output;
5. revoke the old application key;
6. record the rotation in the operational change record.

Broker credential rotation follows `SECRETS-RUNBOOK.md` and remains separate from GitHub Actions.

## Production safety boundary

A green `Production Readiness` workflow is evidence that configured gates passed. It does not grant autonomous execution authority and does not submit an order. Any separately authorized live-equity canary remains limited by the application-side controls and the generated canary plan. GitHub Environment configuration must never be treated as a bypass for those controls.
