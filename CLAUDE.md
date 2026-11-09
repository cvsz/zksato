# CLAUDE.md — Operating Guidelines for Claude in zksato

This file provides guidance for Claude when working on the **zksato** repository.

## Core Mission & Safety Invariants
- `paper` is the default mode.
- Autonomous live-money execution is strictly forbidden. Live orders require explicit operator authorization.
- Never bypass `RiskEngine` or `TradingService`.
- Secret tokens, API keys, PINs, and credentials remain server-side.
- Stale or ambiguous market data must fail closed.

## Required Validation Commands
Before opening or suggesting any commit:
```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh
```

## Multi-Account Git Governance & Sign-Off Workflow

Claude and all coding agents **must** operate through the following exact sequence. Credentials are stored in `/home/cvsz/.git-credentials`; use `gh auth switch` exclusively — never store or hardcode tokens.

> **All commits must be GPG-signed. No exceptions.**

### Step 1 — Author Changes, GPG-Sign, and Open PR as `cvsz`

```bash
gh auth switch -u cvsz
git checkout -b <branch-name>
# Implement changes and verify locally
python -m pip install -e '.[dev]'
ruff check .
pytest
git add -A
git commit -S -m "<commit-message>"
git push -u origin <branch-name>
gh pr create --title "<title>" --body "<body>"
```

### Step 2 — Independent Audit, Review, & Approve as `policedbc`

```bash
gh auth switch -u policedbc
# Perform independent audit of diffs, security gates, and CI checks
gh pr review <pr-number> --approve -b "Independent audit: <audit-summary>"
```

### Step 3 — Squash Merge and Sync as `cvsz`

```bash
gh auth switch -u cvsz
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

