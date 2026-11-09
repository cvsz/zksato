# GitHub Workflow Security Audit (PR #43 Remediation)

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Vulnerability Analysis

Two dangerous workflows previously existed on `main`:
1. `.github/workflows/automated-audit-review-approve.yml`
2. `.github/workflows/auto-fix-open-prs.yml`
Along with `.github/scripts/post-review-comment.sh`.

### Attack Vector
- These workflows checked out pull requests and exposed privileged secrets (`POLIEDBC_PAT`, `GPG_SIGNING_KEY`, `GPG_PASSPHRASE`).
- In `automated-audit-review-approve.yml`, the workflow could automatically submit a GitHub PR review approving changes under the `@policedbc` independent reviewer identity.
- This violated the core security invariant that reviewer credentials must remain isolated from PR-controlled code and fork executions.

## 2. Remediation Actions

1. **Complete Removal**:
   - Deleted `.github/workflows/automated-audit-review-approve.yml`
   - Deleted `.github/workflows/auto-fix-open-prs.yml`
   - Deleted `.github/scripts/post-review-comment.sh`
2. **Regression Test Enforcement**:
   Created `tests/test_workflow_security.py` which:
   - Verifies the deleted files do not exist.
   - Searches all `.github/workflows/*.yml` files to assert no reference to `POLIEDBC_PAT`, `GPG_SIGNING_KEY`, or `GPG_PASSPHRASE`.
   - Asserts PR-triggered workflows do not execute automated `gh pr review` or disable commit signing.
3. **Execution Evidence**:
   ```
   tests/test_workflow_security.py ... [100%]
   3 passed in 0.70s
   ```
