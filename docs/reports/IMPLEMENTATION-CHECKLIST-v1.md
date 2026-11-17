# Implementation & Engineering Checklist — ZKSATO

This checklist tracks complete system verification, financial safety guarantees, security postures, and release engineering standards for **zksato** (`https://github.com/cvsz/zksato`).

---

## 1. Non-Negotiable Financial Safety Invariants

- [x] **Default Paper Mode**: System boots into `paper` execution mode by default.
- [x] **Autonomous Live Execution Forbidden**: Autonomous live money execution is permanently blocked; live orders require human operator approval.
- [x] **RiskEngine & TradingService Boundary**: No LLM, external agent, dashboard, or strategy can bypass risk checks.
- [x] **Credential Isolation**: Broker tokens, API keys, and PINs remain server-side and are never committed or rendered.
- [x] **Fail-Closed on Stale Feeds**: Stale market data or broker disconnects trigger fail-closed state.
- [x] **Reconciliation & Idempotency**: Order submissions maintain durable idempotency keys across retries and restarts.
- [x] **SET vs. TFEX Separation**: Equity board lots and tick rules are kept distinct from TFEX derivative contracts and margin models.

---

## 2. Universal Audit & Vulnerability Remediations

- [x] **PR-Controlled Reviewer Escalation (P0)**:
  - Removed `.github/workflows/automated-audit-review-approve.yml`, `.github/workflows/auto-fix-open-prs.yml`, and `.github/scripts/post-review-comment.sh`.
  - Added automated CI policy assertions in `tests/test_workflow_security.py`.
- [x] **Performance Probe Contract Alignment (P1)**:
  - Reconciled `scripts/load_test.py` with `.github/workflows/performance.yml` (`--url`, `--output`, `--max-failures`, `--max-p95-ms`).
  - Added automated percentile latency computations and unit tests in `tests/test_performance_probe.py`.
- [x] **Docker Compose Portability (P2)**:
  - Configured optional `.env` fallback (`required: false`) in `docker-compose.yml` to prevent crashes when testing clean environments.
- [x] **Security Scanner Resilience (P2)**:
  - Added `--retry 5 --retry-connrefused` to curl downloads in `.github/workflows/security.yml`.
- [x] **ShellCheck Standardization**:
  - Resolved `SC2034`, `SC2155`, `SC1090`, and `SC2086` in `deploy/deploy.sh`.
- [x] **External Advisory Security Boundary**:
  - Bound external signals (zTrader) to `contracts/ztrader-advisory-intent.v1.schema.json`.

---

## 3. Pull Request & Governance Queue Triage

- [x] **PR #46** (`feat(security): comprehensive audit, financial invariants, and workflow security hardening`): Approved by `policedbc` & Merged into `main` (`91ddd0e`).
- [x] **PR #47** (`fix(deploy): resolve shellcheck warnings and harden environment loading in deploy.sh`): Approved by `policedbc` & Merged into `main` (`934e938`).
- [x] **PR #48** (`docs: add implementation-checklist.md covering complete audit and release validation`): Approved by `policedbc` & Merged into `main` (`6d1e471`).
- [x] **PR #49** (`chore(agents): add/update multi-account Git governance workflow in all agent instruction files`): Approved by `policedbc` & Merged into `main` (`60e661e`).
- [x] **PR #51** (`chore(makefile): expand Makefile to cover all project features`): Approved by `policedbc` & Merged into `main` (`41d06ee`).
- [x] **PR #52** (`feat(strategy): add statistical arbitrage and TFEX calendar spread strategies`): Approved by `policedbc` & Merged into `main` (`b38d675`).
- [x] **PR #53** (`build(deps-dev): bump ruff to 0.16.6 and zizmor to 1.30.0`): Approved by `policedbc` & Merged into `main` (`4646633`).
- [x] **PR #54** (`docs(strategy): update feature matrix and strategy catalog`): Approved by `policedbc` & Merged into `main` (`1e177a6`).
- [x] **PR #55** (`docs: update README.md with Agent OS endpoints, full strategy catalog, and system capabilities`): Approved by `policedbc` & Merged into `main` (`e8f679c`).
- [x] **PR #43** (Unsafe reviewer workflow removal): Closed (superceded by PR #46).
- [x] **PR #36** (next bump): Closed (superceded by PR #46).
- [x] **PR #32** (zTrader paper integration): Closed (superceded by PR #46).
- [x] **PR #31** (zTrader advisory boundary docs): Closed (superceded by PR #46).
- [x] **PR #26** (python deps bump): Closed (superceded by PR #53).

---

## 4. Verification & Quality Gates

- [x] **Ruff Linter**: `ruff check .` passes with 0 errors and 0 warnings (ruff 0.16.6).
- [x] **ShellCheck**: `shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh` passes with 0 warnings.
- [x] **Python Pytest Suite**: 360 passed, 1 skipped, 5 deselected.
- [x] **Financial Invariants Suite**: `pytest tests/test_financial_invariants.py` passes all property-based tests.
- [x] **Workflow Security Suite**: `pytest tests/test_workflow_security.py` passes.
- [x] **Zizmor Security Audit**: `zizmor .github/workflows` passes with 0 findings.
- [x] **Performance Probe Suite**: `pytest tests/test_performance_probe.py` passes.
- [x] **Docker Compose Validation**: `docker compose config` validates cleanly.

---

## 5. Multi-Account Sign-Off Verification

- [x] **Author (`cvsz`)**: Authored changes with GPG signed commits (`EDDSA key 8BC7A85F1FB5322782921AEC14E1E0BC08F632B0`).
- [x] **Independent Reviewer (`policedbc`)**: Audited and approved all pull requests.
- [x] **Repository Owner (`cvsz`)**: Squash-merged approved changes into `main`.
