# ZKSATO master prompt — execution and evidence alignment

**Target:** `cvsz/zksato`  
**Baseline:** `main` at the time this branch was created  
**Prompt source:** The 20-section universal engineering master prompt supplied for this task.  
**Purpose:** Translate the prompt into repository-governed execution without duplicating existing architecture or weakening established financial-safety controls.

## Authority and precedence

This execution record supplements, and does not override:

1. `SECURITY.md` and the non-waivable financial execution invariants.
2. `AGENTS.md`, including GPG signing and multi-account review governance.
3. Accepted ADRs under `docs/adr/`.
4. `GOVERNANCE.md`, `CONTRIBUTING.md`, and `docs/ASSURANCE.md`.
5. Domain specifications, implementation, tests, and operational evidence.

In particular, this record does not authorize autonomous live-money execution, broaden TFEX production permissions, bypass `RiskEngine`/`TradingService`, weaken credential boundaries, or declare external broker/deployment gates complete.

## Repository baseline observed

The GitHub repository was inspected on its `main` branch. The repository tree contained 660 entries. Existing major components include:

- Backend: FastAPI/Python package under `src/zksato/`, including risk, service, broker adapters, persistence, reconciliation, production readiness, agent OS, strategies, backtesting, and observability.
- Operator applications: Next.js frontend under `frontend/` and a separate Vite dashboard under `dashboard/`.
- Tests: Python tests under `tests/` and browser E2E tests under `frontend/tests/e2e/`.
- Operations: Docker Compose, deployment scripts, migrations, GitHub workflows, and security/recovery tooling.
- Governance and evidence: `AGENTS.md`, `SECURITY.md`, `GOVERNANCE.md`, `docs/ASSURANCE.md`, `docs/EXECUTION-PLAN.md`, `docs/FEATURE-MATRIX.md`, `docs/PRODUCTION-READINESS.md`, `docs/PRODUCTION-CHECKLIST.md`, and detailed audit reports under `docs/audit/`.

This is a source-tree inventory, not an assertion that every listed capability was exercised in this task.

## Prompt-to-repository coverage map

| Master prompt scope | Existing repository entry points | Verification boundary |
| --- | --- | --- |
| Governance and source of truth | `AGENTS.md`, `SECURITY.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`, `docs/INDEX.md` | Review precedence and required author/reviewer identities before every change |
| Architecture and system flow | `docs/ARCHITECTURE.md`, `docs/SYSTEM-DESIGN.md`, `docs/DOMAIN-MODEL.md`, `docs/adr/` | Confirm implementation matches accepted architecture; do not infer from diagrams alone |
| Backend/API | `src/zksato/api.py`, `src/zksato/service.py`, `src/zksato/risk.py`, `docs/API-SPEC.md` | Compile, type-check, API contract and integration tests |
| Persistence and recovery | `src/zksato/persistence.py`, `migrations/`, `docs/DATABASE.md`, `docs/DR-RUNBOOK.md` | PostgreSQL integration, migration, restart/idempotency, backup and restore evidence |
| Operator UI | `frontend/`, `dashboard/`, `docs/DASHBOARD-*.md`, `skills/dashboard-ui/` | Type-check, lint, production build, E2E, accessibility and API integration |
| Financial risk and order lifecycle | `src/zksato/risk.py`, `src/zksato/service.py`, `src/zksato/reconcile.py`, `docs/RISK.md`, `docs/ORDER-LIFECYCLE.md` | Deterministic unit/property/failure-path tests; require owner review for sensitive changes |
| SET/TFEX and brokers | `src/zksato/broker/`, `src/zksato/tfex.py`, `docs/SETTRADE-INTEGRATION.md`, `docs/TFEX.md`, `docs/UAT-CERTIFICATION.md` | Adapter tests are source-level evidence; broker UAT certification remains external |
| Strategy/backtesting/optimization | `src/zksato/strategy.py`, `src/zksato/backtest*.py`, `src/zksato/hyperopt.py`, `docs/STRATEGY.md`, `docs/BACKTESTING.md` | Deterministic replay, leakage/overfit checks, OOS and strategy-specific evidence |
| Agent OS and LLM boundary | `src/zksato/agent_os/`, `src/zksato/llm_clients/`, `docs/AI-ASSISTANCE.md`, `docs/adr/0005-ai-read-only-boundary.md` | Agent identity/permission tests; LLM output remains advisory and untrusted |
| Security and supply chain | `SECURITY.md`, `docs/THREAT-MODEL.md`, `docs/SUPPLY-CHAIN.md`, security workflows | Static scans, secret scans, workflow validation, container and dependency evidence |
| CI/release/operations | `.github/workflows/`, `docker-compose.yml`, `scripts/`, `docs/ASSURANCE.md` | Exact-head required checks, Compose build, release artifact and operational drills |
| Real-time engineering status | `docs/DASHBOARD.md`, `docs/OBSERVABILITY.md`, `docs/SLO.md`, production readiness APIs | Report measured runtime/task/CI evidence only; no synthetic agent/progress claims |

## Required execution rules

### Financial safety

- Keep `paper` as the default mode.
- Autonomous live-money execution remains prohibited.
- All order mutations must stay behind the trusted server-side risk and execution boundary.
- Keep broker credentials, API keys, PINs, session secrets and approval material server-side.
- Treat broker state as the external source of truth for live reconciliation.
- Unknown broker outcomes must fail closed and enter reconciliation; never blindly retry non-idempotent operations.
- Stale or unknown market data must fail closed for automated execution.
- Preserve separate SET equity and TFEX contract/margin semantics.
- Preserve Agent OS `WITHDRAW=False`.
- Keep TFEX production mutation disabled until the separately governed broker certification gate is satisfied.
- Never use real broker credentials/accounts in routine automated tests.

### Engineering execution

1. Start from the latest `main`; inspect current working branch and outstanding PRs.
2. Read applicable root and nested `AGENTS.md`, Copilot instructions, agent skill files, CODEOWNERS, relevant ADRs, templates, and package manifests.
3. Map each finding to a concrete file, root cause, severity, acceptance criterion and owner.
4. Prefer narrow vertical slices; coordinate file ownership before parallel edits.
5. Include positive, negative, failure, concurrency and restart/idempotency tests appropriate to the changed boundary.
6. Update API/schema/docs/feature matrix/ADR/runbook together when contracts change.
7. Run the exact repository validation required by `CONTRIBUTING.md` and `AGENTS.md`.
8. Inspect the resulting diff, secret exposure, safety invariants, workflow trust boundaries and dependency impact.
9. Produce a PR with rollout and rollback notes for non-trivial work.
10. Do not treat PR creation as independent approval or merge authorization.

### Multi-account and commit governance

Follow `AGENTS.md`: author as `cvsz`, use GPG-signed commits, and obtain a genuinely separate review from `policedbc`. Do not use another identity, simulate an approval, or claim a signature without cryptographic verification. Risk, broker, reconciliation, financial-accounting, authentication, secret-handling and migration changes require explicit specialist review evidence.

## Status vocabulary

Use evidence-backed labels only:

- **IMPLEMENTED_AND_TESTED** — implementation and applicable automated tests were inspected/executed successfully.
- **IMPLEMENTED_BUT_UNVERIFIED** — source implementation exists but this task did not execute the relevant validation.
- **PARTIALLY_IMPLEMENTED** — concrete incomplete code or integration remains.
- **PLACEHOLDER_OR_STUB** — nonfunctional placeholder confirmed in source.
- **MISSING** — required repository capability has no implementation after search.
- **BROKEN** — reproducible failure with command/log/test evidence.
- **BLOCKED_BY_EXTERNAL_DEPENDENCY** — requires broker account, UAT, hosting, credentials, legal approval, GitHub entitlement, or operator evidence.
- **NOT_APPLICABLE** — unsupported by the product's explicit safety/domain policy.

Do not infer status from README/roadmap checkboxes alone. Do not invent a completion percentage.

## Validation commands required by the repository

Execute in a trusted local checkout with the expected toolchain; preserve stdout, stderr and exit codes:

```bash
python -m pip install -e '.[dev,quality,security]'
python -m compileall -q src tests scripts
python -m pip check
ruff check .
ruff format --check .
mypy src/zksato scripts
pytest -m "not uat and not performance"
python scripts/openapi_contract.py
docker compose config
docker build -t zksato:local .
```

Also execute the frontend checks defined by `frontend/package.json`: lint, type-check, unit tests (when configured), and production build; run Playwright E2E in the supported browser environment. Add security/container/workflow/recovery checks relevant to the changed files.

A check is **not run** until its command has actually executed. A GitHub source inspection is not a test run. External UAT, restore drills, real monitoring delivery, capacity evidence and production permissions remain separate gates.

## External acceptance gates — never auto-mark complete

- Settrade equity UAT lifecycle certification and broker permission.
- TFEX certification and any production authorization.
- Target-environment TLS/ingress, managed secrets and access review.
- Backup/restore and disaster-recovery drills with measured RPO/RTO.
- Alert delivery, SLO/capacity, time synchronization and market-data failover evidence.
- Legal/operational approvals and explicit authorization for any manual live canary.
- GitHub environments, rulesets, branch protection and plan-dependent security capabilities.

## Current task execution evidence

| Action | Result |
| --- | --- |
| Read supplied universal master prompt | Done; 20 sections and financial-safety constraints reviewed |
| Read root governance, security, contribution and architecture sources | Done by GitHub file reads |
| Inspect repository metadata and tree | Done; default branch `main`; 660 tree entries observed |
| Inspect open pull requests | No open PRs returned by the connected GitHub account |
| Inspect key existing docs and code entry points | Done selectively; existing coverage is extensive |
| Create isolated working branch | Done: `docs/master-prompt-evidence-alignment-20261112` |
| Local Python/Node/Docker tests | Not run in this connector session |
| GPG-signed commit | Not created; signing key is unavailable through GitHub file APIs |
| Independent `policedbc` review | Not performed |
| Merge/release/deployment | Not performed |

## Next execution backlog

This backlog is intentionally evidence-driven, not a claim that these items are currently broken:

1. Run the complete prescribed validation suite on the branch and capture exact output/exit codes.
2. Compare source implementation against the full prompt map, focusing on high-risk seams: broker ambiguous outcomes, order/fill idempotency, session/reconciliation freshness, stale feed closure, kill paths, auth/IDOR, webhook signatures, agent permissions and frontend authorization.
3. Review frontend routes and every interactive control against live API contracts; remove or label any demo-only behavior that could be mistaken for live state.
4. Execute database migration, restart/recovery, backup/restore and failure-injection tests.
5. Execute workflow/container/dependency/secret scans; remediate only reproducible findings with regression coverage.
6. Obtain external broker UAT and deployment evidence through the governed checklists.
7. Obtain the required independent review and only then consider merge/release.

## Change safety statement

This document is an execution register and evidence index. It does not change trading behavior, risk limits, broker permissions, secrets, migrations, or production environment configuration. It does not constitute broker certification, production authorization, or independent approval.
