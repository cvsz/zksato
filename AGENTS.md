# AGENTS.md — zksato engineering operating contract

<!-- Social Preview -->
<meta property="og:title" content="AGENTS.md — zksato Engineering Operating Contract">
<meta property="og:description" content="Engineering and agent operating contract for zksato — Risk-First SET/TFEX Trading Control Plane. Defines safety invariants, runtime conventions, agent workflow, and multi-account Git governance.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://github.com/cvsz/zksato/blob/main/AGENTS.md">
<meta property="og:site_name" content="zksato">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@cvsz">
<meta name="twitter:creator" content="@cvsz">

This file is the primary instruction set for humans and coding agents working in this repository.

## Mission
Build zksato into a production-grade, risk-first automated trading platform for SET/TFEX while preserving a strict separation between analysis, risk, execution, and broker state.

## Non-negotiable safety invariants
1. `paper` is the default mode.
2. Autonomous live-money execution is forbidden. Live orders require explicit operator authorization at the trusted server boundary.
3. No LLM, agent, browser state, strategy, or dashboard control may bypass `RiskEngine` or `TradingService`.
4. Broker credentials, PINs, tokens, and confirmation secrets stay server-side and must never be committed, logged, rendered, or returned by APIs.
5. Broker state is the external source of truth for live reconciliation; local state must converge to it.
6. Order creation must be idempotent across retries and, once durable persistence is implemented, across restarts.
7. A stale/unknown market feed must fail closed for automated execution.
8. Risk controls must have independent kill paths and failure-path tests.
9. SET and TFEX semantics must not be conflated; derivatives require dedicated margin, contract, and position handling.
10. Any behavior that can move money must be deterministic, auditable, versioned, and testable.

## Runtime conventions
- Python: 3.11+
- API/dashboard port: `9569`
- API: FastAPI
- Test: `pytest`
- Lint: `ruff check .`
- Default local mode: `ZKSATO_TRADING_MODE=paper`
- Docker startup: `docker compose up --build -d`

## Required validation before merging
```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```
For infrastructure changes also run:
```bash
docker compose config
docker compose build
```

## Agent workflow
1. Read `README.md`, `docs/INDEX.md`, `ROADMAP.md`, `docs/FEATURE-MATRIX.md`, and the relevant agent/skill files.
2. Inspect current code and tests before proposing a change.
3. State the invariant being changed or protected.
4. Prefer a narrow vertical slice over broad partial scaffolding.
5. Add/update tests with the implementation.
6. Update relevant docs, API contracts, ADRs, runbooks, and feature matrix.
7. Run CI-equivalent checks.
8. Use a PR for non-trivial changes; include rollout and rollback notes.

## Definition of done
A feature is done only when it has: implementation, validation, failure behavior, observability, documentation, security/risk review where applicable, deployment/rollback notes, and no unresolved P0/P1 correctness issue.

## Repository ownership map
- Market data: `src/zksato/market.py` → `agents/market-data-agent.md`
- Strategy/indicators: `strategy.py`, `indicators.py` → `agents/strategy-agent.md`, `agents/ai-research-agent.md`
- Risk: `risk.py` → `agents/risk-agent.md`
- Execution/broker: `service.py`, `broker/` → `agents/execution-agent.md`, `agents/broker-integration-agent.md`
- Portfolio: `portfolio.py` → `agents/portfolio-agent.md`
- Automation: `automation.py` → `agents/orchestrator-agent.md`
- Dashboard/API: `api.py`, `dashboard.py` → `agents/dashboard-agent.md`
- Persistence: future DB/Redis adapters → `agents/persistence-agent.md`
- Security: auth/secrets/threat model → `agents/security-agent.md`
- Operations: Docker/CI/deploy/observability → `agents/devops-agent.md`, `agents/observability-agent.md`
- Documentation/releases → `agents/docs-agent.md`, `agents/release-agent.md`
- Architecture/design: `docs/ARCHITECTURE.md`, `docs/SYSTEM-DESIGN.md` → `agents/architecture-agent.md`
- Incident response: runbooks, dr drills → `agents/incident-agent.md`
- Testing: `tests/` → `agents/testing-agent.md`
- TFEX domain: `src/zksato/tfex/` → `agents/tfex-agent.md`

## Change classes requiring explicit review
- Risk formulas/limits
- Live execution policy
- Broker API calls or credential handling
- Order idempotency/reconciliation
- Position/P&L accounting
- TFEX margin/contract handling
- Authentication/authorization
- Database migrations affecting orders, fills, positions, risk decisions, audit events

## Documentation precedence
When docs conflict, use this order: `SECURITY.md` and live-execution invariants → `AGENTS.md` → accepted ADRs → `docs/API-SPEC.md`/`docs/DATABASE.md`/`docs/DOMAIN-MODEL.md` → implementation notes. Fix the conflict in the same PR.

## Multi-Account Git Governance & Sign-Off Workflow

All automated agents and developers **must** strictly follow the authenticated multi-account separation of duties below. Credentials are managed via `/home/cvsz/.git-credentials`; account switching is performed exclusively through `gh auth switch`.

> **Never commit, push, or merge under a different account than specified. Never skip GPG signing on commits.**

### Step 1 — Author, GPG-Sign, and Open PR as `cvsz`

```bash
gh auth switch -u cvsz
git checkout -b <feature-or-fix-branch>
# Implement changes, run full validation suite
python -m pip install -e '.[dev]'
ruff check .
pytest
# Stage and sign-commit
git add -A
git commit -S -m "<type>(<scope>): <summary>"
git push -u origin <feature-or-fix-branch>
gh pr create --title "<title>" --body "<body>"
```

### Step 2 — Independent Audit, Review, & Approval as `policedbc`

```bash
gh auth switch -u policedbc
# Review PR diff, security posture, CI status, and test evidence
gh pr review <pr-number> --approve -b "Independent audit: <review-summary>"
```

### Step 3 — Squash Merge and Sync as `cvsz`

```bash
gh auth switch -u cvsz
gh pr merge <pr-number> --squash --delete-branch
git checkout main && git pull origin main
```

