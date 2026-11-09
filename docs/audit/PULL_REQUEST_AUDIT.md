# Pull Request Audit Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Inventory of Open Pull Requests

| PR # | Title | Branch | Status & Evaluation |
| :--- | :--- | :--- | :--- |
| **#45** | build(deps): bump the github-actions group | `dependabot/github_actions/...` | **Integrated**: Updated `docker/login-action` to 4.8.0 and `codeql-action` to 33d7b85. |
| **#43** | security: remove PR-controlled reviewer credential workflow | `security/remove-unsafe...` | **Remediated**: Removed both `automated-audit-review-approve.yml` and `auto-fix-open-prs.yml`, plus `post-review-comment.sh`. Added regression test `tests/test_workflow_security.py`. |
| **#36** | build(deps): bump next from 16.3.3 to 16.3.6 | `dependabot/npm_and_yarn/...` | **Integrated**: Updated `next` to 16.3.6 in `frontend/package.json` and `package-lock.json`. Fixed build script with `--webpack`. |
| **#32** | feat: add paper-only zTrader advisory integration | `feat/ztrader-advisory...` | **Hardened & Reconciled**: Added tenant/account namespace isolation to `_ztrader_advisory_key` to address policedbc review. |
| **#31** | docs: define zTrader advisory execution boundary | `integrate/ztrader-ad...` | **Integrated**: Integrated `contracts/ztrader-advisory-intent.v1.schema.json` and `docs/integrations/ZTRADER_ADVISORY_INTENT.md`. |
| **#26** | build(deps-dev): bump python dependencies | `dependabot/pip/...` | **Evaluated & Verified**: `ruff` and `zizmor` tested and passing cleanly in `.venv`. |

---

## 2. Remediation Strategy

All findings, fixes, and updates across PR #45, #43, #36, #32, #31, and #26 have been unified and tested on branch `feat/zksato-universal-remediation`.
