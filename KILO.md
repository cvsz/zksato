# KILO.md — Operating & Engineering Instructions for Kilo in zksato

This file defines guidelines and execution boundaries for Kilo agents in **zksato**.

## Architecture & Financial Invariants
- `paper` trading is the default mode.
- Autonomous live trading is strictly forbidden.
- AI models are advisory-only; all trades require server-side deterministic `RiskEngine` validation.
- All broker and user secrets stay server-side and are never committed or logged.
- Financial arithmetic must use exact representations and respect SET board lots vs. TFEX contract specifications.

## Required Pre-Merge Verification
```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh
```

## Multi-Account Git Governance & Sign-Off Workflow

Kilo **must** strictly follow the authenticated separation of duties below. Credentials are managed via `/home/cvsz/.git-credentials`; use `gh auth switch` exclusively.

> **All commits must be GPG-signed (`git commit -S`). Never merge without an independent approval from `policedbc`.**

### Step 1 — Commit and Open PR as `cvsz`

```bash
gh auth switch -u cvsz
git checkout -b <branch-name>
python -m pip install -e '.[dev]'
ruff check .
pytest
git add -A
git commit -S -m "<commit-message>"
git push -u origin <branch-name>
gh pr create --title "<title>" --body "<body>"
```

### Step 2 — Independent Audit & Approval as `policedbc`

```bash
gh auth switch -u policedbc
# Review diffs, security invariants, CI status, and test evidence
gh pr review <pr-number> --approve -b "Independent audit passed: <evidence-summary>"
```

### Step 3 — Squash Merge as `cvsz`

```bash
gh auth switch -u cvsz
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

