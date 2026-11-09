# AGY.md — Operating Instructions for Antigravity (AGY) in zksato

This file governs **Antigravity (AGY / Antigravity CLI)** agents and all subagents they spawn while operating in the **zksato** repository.

## Core Mission & Safety Invariants

- `paper` is the **default and mandatory** mode. Never generate, suggest, or execute live-order logic without explicit operator authorization at the trusted server boundary.
- Autonomous live-money execution is permanently forbidden.
- AGY output and all subagent output is **advisory only**. All order flow must pass through `RiskEngine` and `TradingService`.
- Never generate, log, print, return, or embed broker credentials, PINs, API secrets, tokens, or confirmation codes in code, comments, test fixtures, artifacts, or agent responses.
- Stale or ambiguous market data must fail closed for all automated execution paths.
- SET and TFEX semantics must never be conflated; derivatives require dedicated margin, contract, and position handling.
- Any behavior that can move money must be deterministic, auditable, versioned, and testable.

## Required Pre-Commit Validation

Run these checks before authoring any commit:

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh
```

For infrastructure or Docker changes also run:

```bash
docker compose config
docker compose build
```

## Multi-Account Git Governance & Sign-Off Workflow

AGY agents **must** enforce the following separation of duties using credentials in `/home/cvsz/.git-credentials` and `gh auth switch`. No shortcuts or account merges are permitted. Subagents spawned by AGY inherit this obligation.

> **All commits must be GPG-signed (`git commit -S`). The `policedbc` independent review is mandatory before any merge.**

### Step 1 — Author Changes, GPG-Sign, and Open PR as `cvsz`

```bash
gh auth switch -u cvsz
git checkout -b <feature-or-fix-branch>
# Implement changes and verify locally
python -m pip install -e '.[dev]'
ruff check .
pytest
git add -A
git commit -S -m "<type>(<scope>): <summary>"
git push -u origin <feature-or-fix-branch>
gh pr create --title "<title>" --body "<body>"
```

### Step 2 — Independent Audit, Review, & Approve as `policedbc`

```bash
gh auth switch -u policedbc
# Review PR diff, security posture, CI status, and test evidence independently
gh pr review <pr-number> --approve -b "Independent audit: <review-and-audit-summary>"
```

### Step 3 — Squash Merge and Sync as `cvsz`

```bash
gh auth switch -u cvsz
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

## Agent Workflow

1. Read `README.md`, `docs/INDEX.md`, `ROADMAP.md`, `docs/FEATURE-MATRIX.md`, and relevant agent files in `agents/`.
2. Inspect current code and tests before proposing any change.
3. State the invariant being changed or protected.
4. Prefer a narrow vertical slice over broad partial scaffolding.
5. Add or update tests alongside the implementation.
6. Update relevant docs, API contracts, ADRs, runbooks, and the feature matrix.
7. Run CI-equivalent checks (see above).
8. Use the three-step PR workflow above for all non-trivial changes; include rollout and rollback notes.

## Change Classes Requiring Extra Scrutiny

Before authoring changes in any of these areas, explicitly state the invariant being protected:

- Risk formulas, limits, and kill paths
- Live execution policy
- Broker API calls or credential handling
- Order idempotency / reconciliation
- Position / P&L accounting
- TFEX margin and contract handling
- Authentication / authorization
- Database migrations affecting orders, fills, positions, risk decisions, or audit events

## Subagent Delegation Rules

- All subagents spawned by AGY inherit these invariants in full.
- Research or read-only subagents must not write, commit, push, or call broker APIs.
- Write-capable subagents must follow the full three-step PR workflow.
- No subagent may bypass `RiskEngine` or access live-execution paths without explicit operator approval surfaced to the AGY parent.

## Repository Ownership Map

Refer to `AGENTS.md` for the full ownership map and agent routing table.

## Documentation Precedence

`SECURITY.md` and live-execution invariants → `AGENTS.md` → accepted ADRs → `docs/API-SPEC.md` / `docs/DATABASE.md` / `docs/DOMAIN-MODEL.md` → implementation notes.
