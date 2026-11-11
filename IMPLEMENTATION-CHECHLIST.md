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

## 2. Freqtrade Strategy Framework Integration (PR #72, #73)

- [x] **IStrategy Interface** (`src/zksato/strategy_freqtrade.py`):
  - `populate_indicators()` — deterministic indicator calculation
  - `populate_entry_trend()` — entry signal generation with tags
  - `populate_exit_trend()` — exit signal generation with tags
  - `signal_to_intent()` — conversion to zksato OrderIntent (routed through RiskEngine)
  - Hyperoptable parameters (`IntParameter`, `DecimalParameter`, `CategoricalParameter`, `BooleanParameter`)
  - ROI table (`max_notional_per_order` style stop-loss/take-profit tables)
  - Trailing stop configuration (`trailing_stop_positive`, `trailing_stop_positive_offset`)
  - Protections integration (cooldown, stoploss guard, drawdown protection)
- [x] **Example Strategies**:
  - `ema_cross` — EMA fast/slow cross with entry/exit tags
  - `rsi_reversion` — RSI oversold/overbought reversion
- [x] **Strategy Registry** (`strategy_registry`) — register/instantiate/list strategies
- [x] **Enhanced Backtesting** (`src/zksato/backtest_enhanced.py`):
  - Sharpe, Sortino, Calmar, SQN, Profit Factor, Expectancy metrics
  - Drawdown analysis with drawdown duration
  - Pair-level performance breakdown
  - Exit reason statistics
  - Entry tag performance breakdown
  - Position sizing statistics (avg/max/min position size %)
  - Order expiration tracking
- [x] **Hyperopt Engine** (`src/zksato/hyperopt.py`):
  - Optuna-based Bayesian hyperparameter optimization
  - 8 loss functions: OnlyProfit, Sharpe, SharpeDaily, Sortino, Calmar, MaxDrawDown, ProfitDrawDown, ShortTradeDur
  - Trial tracking with full parameter and metric history
  - Best trial selection and parameter application
- [x] **Validation**: All new code passes `ruff check`, `ruff format`, `mypy`, and `pytest` (361 tests).

---

## 3. Agent-Native Trading Platform (AI-Trader Inspired) (PR #74, #75)

- [x] **Agent Models** (`src/zksato/agent_trading/models.py`):
  - `Agent` — id, name, email, password_hash, token, wallet_address, role, identity_status, is_verified, cash, deposited, points, reputation_score
  - `AgentRegisterRequest`, `AgentLoginRequest`, AgentTokenRecoveryRequest/Confirm, AgentPasswordResetRequest/Confirm
  - `AgentInfo`, `AgentHeartbeatResponse`
  - Roles: MEMBER, OPERATOR, ADMIN; IdentityStatus: NORMAL, VERIFIED
- [x] **Agent Service** (`src/zksato/agent_trading/service.py`):
  - Registration with idempotency checks
  - Login with password verification (salted SHA-256)
  - Token generation and rotation
  - Heartbeat endpoint — pending messages and tasks polling
  - Points/rewards system: signal publish (+10), discussion publish (+10), reply (+2), accept reply (+3)
  - Points exchange for cash (1 point = 1,000 USD)
  - Agent permissions based on role
- [x] **StateStore Extensions** (`src/zksato/store.py`):
  - Agent CRUD operations (create, get by ID, get by name)
  - Token generation and rotation
  - Agent message storage and retrieval (unread messages, mark as read)
  - Agent task management (pending tasks)
- [x] **Social Preview Meta Tags**: Added OG/Twitter meta tags to `README.md`, `Final-Report.md`, `AGENTS.md`, `SECURITY.md`, `ROADMAP.md`

---

## 4. Universal Audit & Vulnerability Remediations

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
- [x] **Admin .env Control Panel Security**:
  - Raw `.env` content redacted on GET (secret values masked as `********`).
  - `.env.bak` written with `chmod 0o600`.
  - `.env.backup-*` added to `.gitignore`.

---

## 5. Pull Request & Governance Queue Triage

- [x] **PR #46** (`feat(security): comprehensive audit, financial invariants, and workflow security hardening`): Approved by `policedbc` & Merged into `main` (`91ddd0e`).
- [x] **PR #47** (`fix(deploy): resolve shellcheck warnings and harden environment loading in deploy.sh`): Approved by `policedbc` & Merged into `main` (`934e938`).
- [x] **PR #48** (`docs: add implementation-checklist.md covering complete audit and release validation`): Approved by `policedbc` & Merged into `main` (`6d1e471`).
- [x] **PR #49** (`chore(agents): add/update multi-account Git governance workflow in all agent instruction files`): Approved by `policedbc` & Merged into `main` (`60e661e`).
- [x] **PR #51** (`chore(makefile): expand Makefile to cover all project features`): Approved by `policedbc` & Merged into `main` (`41d06ee`).
- [x] **PR #52** (`feat(strategy): add statistical arbitrage and TFEX calendar spread strategies`): Approved by `policedbc` & Merged into `main` (`b38d675`).
- [x] **PR #53** (`build(deps-dev): bump ruff to 0.16.6 and zizmor to 1.30.0`): Approved by `policedbc` & Merged into `main` (`4646633`).
- [x] **PR #54** (`docs(strategy): update feature matrix and strategy catalog`): Approved by `policedbc` & Merged into `main` (`1e177a6`).
- [x] **PR #55** (`docs: update README.md with Agent OS endpoints, full strategy catalog, and system capabilities`): Approved by `policedbc` & Merged into `main` (`e8f679c`).
- [x] **PR #56** (`docs: update CHANGELOG.md and implementation-checklist.md with latest releases`): Approved by `policedbc` & Merged into `main` (`206df8f`).
- [x] **PR #68** (`fix(security): harden admin env endpoint, session cookies, and idempotency across restarts`): Approved by `policedbc` & Merged into `main` (`2298c23`).
- [x] **PR #69** (`fix(security): harden env validation, CI security gates, and gitignore coverage`): Approved by `policedbc` & Merged into `main` (`8bfb4e8`).
- [x] **PR #70** (`docs(final-report): add Medium/Low security remediation findings and PR #68/#69 governance history`): Approved by `policedbc` & Merged into `main` (`66ef7db`).
- [x] **PR #71** (`docs(final-report): document comprehensive source code investigation findings`): Approved by `policedbc` & Merged into `main` (`e6cf6f4`).
- [x] **PR #72** (`feat(freqtrade): integrate Freqtrade-inspired strategy framework, hyperopt, backtesting, protections, pairlist, LLM clients`): Approved by `policedbc` & Merged into `main` (`6565646`).
- [x] **PR #73** (`feat(freqtrade): refactor strategy framework with entry/exit tags, position stacking, order expiration, market regime detection`): Approved by `policedbc` & Merged into `main` (`3e19d97`).
- [x] **PR #74** (`feat(agent-os): add agent-native trading platform layer`): Approved by `policedbc` & Merged into `main` (`131416f`).
- [x] **PR #75** (`feat(agent-os): add agent-native trading platform layer with social preview meta tags`): Approved by `policedbc` & Merged into `main` (`eb10a38`).
- [x] **PR #43** (Unsafe reviewer workflow removal): Closed (superceded by PR #46).
- [x] **PR #36** (next bump): Closed (superceded by PR #46).
- [x] **PR #32** (zTrader paper integration): Closed (superceded by PR #46).
- [x] **PR #31** (zTrader advisory boundary docs): Closed (superceded by PR #46).
- [x] **PR #26** (python deps bump): Closed (superceded by PR #53).

---

## 6. Verification & Quality Gates

- [x] **Ruff Linter**: `ruff check .` passes with 0 errors and 0 warnings (ruff 0.16.6).
- [x] **Ruff Format**: `ruff format --check .` passes (403 files clean).
- [x] **Mypy Static Type Checking**: `mypy src/zksato scripts` passes with 0 errors (86 source files).
- [x] **ShellCheck**: `shellcheck scripts/*.sh deploy/*.sh .github/scripts/*.sh` passes with 0 warnings.
- [x] **Python Pytest Suite**: 361 passed, 1 skipped, 5 deselected (`pytest -m "not uat and not performance"`).
- [x] **Financial Invariants Suite**: `pytest tests/test_financial_invariants.py` passes all property-based tests.
- [x] **Workflow Security Suite**: `pytest tests/test_workflow_security.py` passes.
- [x] **Zizmor Security Audit**: `zizmor .github/workflows` passes with 0 findings.
- [x] **Performance Probe Suite**: `pytest tests/test_performance_probe.py` passes.
- [x] **Docker Compose Validation**: `docker compose config` validates cleanly.

---

## 7. Multi-Account Sign-Off Verification

- [x] **Author (`cvsz`)**: Authored changes with GPG signed commits (`EDDSA key 8BC7A85F1FB5322782921AEC14E1E0BC08F632B0`).
- [x] **Independent Reviewer (`policedbc`)**: Audited and approved all pull requests (#46 through #75).
- [x] **Repository Owner (`cvsz`)**: Squash-merged approved changes into `main`.

---

## 8. In Progress / Next Steps

- [x] **Additional Strategies**: Added MACD cross (PR #76), Bollinger Band Reversion (PR #78), and Stochastic Oscillator (PR #80) to `src/zksato/strategy_freqtrade.py`. Remaining: Williams %R (PR #82), ATR channel.
- [x] **Frontend Integration**: Frontend directory exists at `/frontend/` with Next.js 16 operator UI.
- [x] **API Endpoints**: 20+ endpoints mounted at `/v1/freqtrade/*` and `/api/claw/*` in `src/zksato/api_freqtrade.py`.
- [ ] **Additional Test Coverage**: Add unit tests for agent trading, hyperopt, and enhanced backtesting modules.
- [ ] **Documentation**: Update `docs/API-SPEC.md`, `docs/DOMAIN-MODEL.md`, `docs/RISK.md` with new modules.
- [ ] **ADRs**: Create `docs/adr/004-agent-native-platform.md`, `docs/adr/005-freqtrade-integration.md`.

---

<footer>
Last updated: 2026-11-11 | Repository: https://github.com/cvsz/zksato | Branch: main
</footer>