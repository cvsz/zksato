# OPENCODE.md — OpenCode Orchestration & Operating Rules for zksato

This file governs OpenCode agents and automated workflows operating in **zksato**.

## Mandatory Operating Principles
1. Default execution is strictly `paper`.
2. Autonomous live trading is permanently disabled.
3. Every order must pass through `RiskEngine` and `TradingService`.
4. Never expose API secrets, broker credentials, or tokens in logs, artifacts, or code.
5. Invariants and property tests (`tests/test_financial_invariants.py`, `tests/test_workflow_security.py`) must never be disabled or bypassed.

## Local Validation Standards
```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh
```

## Mandatory Multi-Account Governance Protocol

Use `/home/cvsz/.git-credentials` and `gh auth switch` to enforce separation of duties. **Never bypass this workflow.**

> **All commits must be GPG-signed. The `policedbc` approval step is mandatory and must not be skipped.**

### Step 1 — Commit & PR Creation as `cvsz`

```bash
gh auth switch -u cvsz
git checkout -b <feature-or-fix-branch>
python -m pip install -e '.[dev]'
ruff check .
pytest
git add -A
git commit -S -m "<type>(<scope>): <summary>"
git push -u origin <feature-or-fix-branch>
gh pr create --title "<title>" --body "<body>"
```

### Step 2 — Independent Review & Approval as `policedbc`

```bash
gh auth switch -u policedbc
# Verify CI results, security gates, and perform independent review
gh pr review <pr-number> --approve -b "Independent security, architecture, and invariant review passed: <summary>"
```

### Step 3 — Final Merge as `cvsz`

```bash
gh auth switch -u cvsz
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

