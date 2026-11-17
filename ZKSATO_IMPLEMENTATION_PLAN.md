# zksato Implementation Plan — Upgrade & Integration

## Overview

This plan documents the current state of zksato, identifies missing form/feature integration from the TradingAgents framework, and provides a structured upgrade path. The goal is to bring zksato to production-grade status while preserving all 10 risk-first safety invariants defined in AGENTS.md.

---

## 1. Codebase Feature Dive

### 1.1 zksato Core Architecture

zksato is a Python monorepo FastAPI-based automated trading platform with the following key components:

**Domain Models** (`src/zksato/domain.py`):
- `OrderIntent`, `OrderSubmission`, `OrderRecord`, `OrderStatus`
- `RiskContext`, `RiskDecision`, `RiskEvaluation`
- `Position`, `PortfolioSnapshot`, `AccountSnapshot`
- `StrategyConfig`, `StrategyVersion`, `StrategyRun`
- `Signal`, `AlertRule`, `AuditEvent`, `OutboxMessage`
- `ScannerResult`, `DashboardSnapshot`

**Trading Service** (`src/zksato/service.py`):
- `TradingService` — central orchestrator with risk engine integration
- `RiskEngine` evaluation and pre-trade validation
- Broker order placement with reconciliation
- Execution policy enforcement (paper/live/sandbox modes)
- Order cancellation and ambiguous outcome handling

**Agent OS** (`src/zksato/agent_os/`):
- `AgentExecutionEngine` — orchestrator enforcing confirm-before-execute protocols
- `AgentSkillHub` — skill registration and execution pattern
- `AgentSubAccountManager` — isolated sub-accounts with permission system
- Core skills: `get_market_quote`, `get_account_summary`, `calculate_technical_indicator`, `submit_guarded_order`, `cancel_agent_order`

**Configuration** (`src/zksato/config.py`):
- `Settings` — Pydantic-settings with environment variable prefix `ZKSATO_`
- Trading mode: `paper` (default), `sandbox`, `live`
- Risk limits, broker credentials, API settings, notification settings
- Automatic secret file reading from mounted secret directory

**API** (`src/zksato/api.py`):
- FastAPI application on port 9569
- Authentication via `AuthManager` with role-based access
- Endpoints: `/v1/orders`, `/v1/risk/preflight`, `/v1/live-approvals`, `/v1/reconcile`, `/v1/bot/start|stop|tick`
- Live approval flow: four-eyes pattern with intent-bound approval tokens
- TFEX-specific endpoints for SET/TFEX derivatives

**Dashboard** (`src/zksato/dashboard.py`):
- HTML dashboard with Vite-injected Miro modules
- Market watch, portfolio, orders, signals, alerts, audit trail
- Order submission with live approval four-eyes flow
- TFEX UAT mutation control panel
- Video EA research panel

**Broker Adapters** (`src/zksato/broker/`):
- `PaperBroker` — paper trading simulation
- `SettradeBroker` — SET (Thailand) broker integration
- `CCXTBroker` — CCXT exchange adapter framework

**Risk Engine** (`src/zksato/risk.py`):
- Comprehensive risk checks: concentration, daily loss limit, drawdown, spread, staleness, price deviation, tick size, sector exposure
- Fail-closed behavior on stale market data
- Independent kill switch path

### 1.2 TradingAgents Framework Comparison

TradingAgents is a Python framework for LLM-powered trading agents with these key features:

**Dataflows & Vendors** (`tradingagents/dataflows/`):
- Modular vendor system (alpha_vantage, yfinance, FRED, Polymarket, SEC-EDGAR, etc.)
- Router pattern with fallback chains
- Category-based tool organization (core_stock_apis, technical_indicators, fundamental_data, news_data, macro_data, prediction_markets)
- `route_to_vendor()` with explicit vendor configuration, no silent fallback

**Agent Architecture** (`tradingagents/agents/`):
- `context.py` — instrument identity resolution, language localization
- `tools.py` — LangChain-registered tools (`get_stock_data`, `get_indicators`, `get_fundamentals`, etc.)
- `analysts/` — researcher, analyst, debater agents
- `risk_mgmt/` — debator patterns for risk discussion
- `post_screen.py` — response screening and validation

**Reporting & Graphs** (`tradingagents/`):
- `report_html.py` — HTML report generation
- `graph/trading_graph.py` — trade graph with checkpoint propagation
- `dataflows/config.py` — configuration management
- `dataflows/date_window.py` — trade date boundary handling

**Key Differences — Missing Forms in zksato:**

| Feature | TradingAgents | zksato | Status |
|---------|--------------|---------|--------|
| Vendor router with explicit config | ✅ `route_to_vendor()` with `data_vendors`/`tool_vendors` | ❌ Hardcoded market feeds | **Missing** — needs adapter plugin system |
| LangChain tool pattern | ✅ `@tool` decorated functions with `|` operator | ❌ No tool registry pattern | **Missing** — should adopt skill hub pattern |
| Instrument identity resolution | ✅ `resolve_instrument_identity()` with company name/sector anchoring | ❌ No identity anchoring against hallucination | **Missing** — should add `domain.py` identity fields |
| Debate/risk discussion pattern | ✅ `conservative_debator.py` / `aggressive_debator.py` | ❌ No agent disagreement framework | **Missing** — optional for multi-agent scenarios |
| HTML report generation | ✅ `report_html.py` with fixed formatting | ❌ Dashboard is inline HTML in Python | **Missing** — could extract to separate template |
| Date window boundary enforcement | ✅ `as_of_window()` prevents post-decision data leakage | ❌ Basic quote age check only | **Missing** — should add vintage-aware data fetching |
| Prediction market integration | ✅ Polymarket integration with `get_prediction_markets` | ❌ Limited prediction support | **Missing** — could add `prediction_feed` integration |
| Multi-vendor fallback strategy | ✅ Explicit config: "yfinance,alpha_vantage" | ❌ Single primary feed with stale data fail-closed | **Different approach** — zksato's fail-closed is intentional for risk |
| Agent skill parameters via Pydantic | ⚠️ Partial (skills defined in Python) | ⚠️ Partial (skills in engine.py) | **Alignment** — normalize skill schemas |
| Outbox/delivery pattern | ⚠️ Basic | ✅ `zksato/outbox_delivery.py` with retry/dead letter | **zksato has stronger pattern** |

---

## 2. Missing Form Integration from TradingAgents

The following "forms" (data models, validation patterns, API schemas) from TradingAgents need to be integrated or adapted for zksato:

### 2.1 Vendor Adapter Form (Market Data)

**TradingAgents pattern**: `VENDOR_METHODS` dict mapping methods to vendor implementations with explicit config.

**zksato gap**: Market data feeds are hardcoded (`DemoMarketFeed`, `CcxtMarketFeed`, `SettradeRealtimeFeed`). Need adapter plugin system.

**Action**: Create `packages/zksato-market/` with adapter protocol similar to `zksato-broker/` pattern. Define `MarketFeed` ABC with `get_quote()`, `get_prices()`, `subscribe()` methods. Implement adapters for:
- `DemoMarketFeed` → paper trading
- `CcxtMarketFeed` → CCXT exchange integration
- `SettradeRealtimeFeed` → SET broker realtime feed
- `PredictionMarketFeed` → Polymarket integration

### 2.2 Tool/ Skill Registration Form

**TradingAgents pattern**: LangChain `@tool` decorators with `InjectedState` for trade_date propagation.

**zksato gap**: Agent skills are bootstrapped manually in `engine.py._bootstrap_core_skills()`. No standardized schema propagation.

**Action**: Formalize skill hub with Pydantic-validated parameter schemas. Add skill injection pattern similar to TradingAgents `InjectedState` for `trade_date`, `symbol`, `curr_date` propagation across skills.

### 2.3 Instrument Identity Form

**TradingAgents pattern**: `resolve_instrument_identity()` resolves company name, sector, exchange anchoring agents against hallucination.

**zksato gap**: No identity anchoring in order intent or market features. Models like `OrderIntent` lack company_name/sector fields.

**Action**: Enhance `domain.py` models:
- Add `company_name: str | None = None` to `Quote`, `Bar`, `OrderIntent`
- Add `sector: str | None = None` to `RiskContext`
- Add identity resolution skill similar to TradingAgents `_identity()`

### 2.4 Report/Output Form

**TradingAgents pattern**: `report_html.py` with fixed HTML template + `report_or_absent()` for empty findings.

**zksato gap**: Dashboard HTML is inline in `dashboard.py`. No standardized report format for audit/findings.

**Action**: Extract dashboard HTML to separate template files. Add `Report` model class similar to TradingAgents `ReconciliationReport`. Implement `report_or_absent()` pattern for audit sections.

### 2.5 Date Window Form

**TradingAgents pattern**: `as_of_window()` and `as_of()` enforce trade_date boundaries, preventing post-decision data leakage.

**zksato gap**: Only `quote_age_seconds` staleness check. No vintage-aware window enforcement.

**Action**: Add `date_window.py` module with `as_of()`, `as_of_window()` functions. Integrate into `service.risk_context_for()` and skill handlers to stamp all data with trade_date.

### 2.6 Outbox Delivery Form

**Comparison**: zksato already has stronger outbox pattern (`zksato/outbox_delivery.py`) with retry, dead-letter, and correlation ID tracking.

**Status**: No change needed — zksato leads on this feature.

---

## 3. Upgrade Path

### Phase 1: Foundation & Modularity (Weeks 1-3)

**1.1 Convert to UV Monorepo Workspace**
- Root `pyproject.toml` already exists with UV setup
- Split `src/zksato/` into domain packages under `packages/`
- Create packages: `zksato-core`, `zksato-risk`, `zksato-market`, `zksato-broker`, `zksato-strategy`, `zksato-portfolio`, `zksato-automation`, `zksato-api`, `zksato-dashboard`, `zksato-cli`, `zksato-test-utils`
- Each package has own `pyproject.toml`, `src/`, `tests/`
- Shared `zksato-test-utils` for fixtures/harnesses
- Deliverable: `uv sync` installs all packages; `uv run pytest` works cross-package

**1.2 Configuration System Overhaul**
- Adopt TOML for complex config (trading rules, risk policies, broker adapters)
- Use `pydantic-settings` with `toml` config file support
- Define JSON schemas for all config sections (auto-generated from Pydantic)
- Config validation at startup with clear error messages
- Environment-specific config files (`.config.dev.toml`, `.config.uat.toml`)
- Files: `config/settings.toml`, `config/settings.local.toml`, `config/schemas/*.json`

**1.3 Core Domain Models Package (`zksato-core`)**
- Split `domain.py` into: `orders.py`, `fills.py`, `positions.py`, `accounts.py`, `events.py`
- `types.py` for shared enums, constants, type aliases
- `utils/` for serialization, datetime, money handling
- `exceptions.py` for domain-specific exceptions
- `ids.py` for idempotency keys, correlation IDs, ULIDs
- Principle: Zero dependencies on other zksato packages

### Phase 2: Risk Engine & Policy Framework (Weeks 3-5)

**2.1 Policy Engine for Risk Rules**
- Create `zksato-risk` package with `PolicyEngine` class
- Risk rules as declarative policies (YAML/TOML), not hardcoded
- Policy evaluation with audit trail (decision + reason + context)
- Support for "approval modes" (paper, sandbox, uat, live) with escalating gates
- Four-eyes policy for live execution (dual authorization)

**Policy Example** (`policies/risk/trading.toml`):
```toml
[policy.daily_loss_limit]
type = "notional"
limit = 50000
currency = "THB"
action = "reject"
approval_mode = "live"

[policy.position_concentration]
type = "concentration"
max_single_symbol_pct = 0.15
max_sector_pct = 0.30
action = "warn"

[policy.feed_freshness]
type = "staleness"
max_age_ms = 5000
action = "fail_closed"
```

**2.2 Risk Engine Refactor**
- Extract `RiskEngine` into `zksato-risk` package
- Make risk checks composable (chain of responsibility)
- Add risk evaluation metrics (latency, decisions, overrides)
- Property-based tests for risk invariants (Hypothesis)

### Phase 3: Agent Orchestration & Automation (Weeks 5-8)

**3.1 Scheduler & Tool Execution Framework**
- Create `zksato-automation` package with `AgentScheduler`
- Tool registry pattern for trading operations (place_order, cancel, query_position)
- Hook system: pre-trade, post-trade, on-error, on-fill
- Parallel execution with configurable concurrency limits
- Checkpointing for long-running strategies (resume after restart)

**3.2 Agent OS Enhancement**
- Event-sourced agent sessions (append-only event log)
- Sub-account isolation with resource quotas
- Skill registry for trading capabilities (market-data, order-entry, risk-check)
- Streaming API for real-time agent updates (SSE/WebSocket)
- Agent-to-Agent (A2A) protocol for multi-agent workflows

**3.3 Background Workers**
- Reconciliation worker (scheduled + event-driven)
- Alert/notification worker (outbox pattern, already exists)
- Market data ingestion worker
- Strategy evaluation worker (scheduled ticks)
- Health/checkpoint worker

### Phase 4: Broker & Market Adapters (Weeks 8-10)

**4.1 Adapter Plugin System**
- Define `BrokerAdapter` protocol in `zksato-broker`
- Plugin entry points for dynamic discovery
- Built-in adapters: `PaperBroker`, `SettradeBroker`, `CCXTBroker`
- Adapter health checks, capability reporting
- Sandbox mode per adapter (isolated test environments)

**4.2 Market Data Pipeline**
- Normalize market data into canonical `Bar`, `Quote`, `Trade` types
- Multi-source feed with fallback (primary → secondary → cached)
- Freshness/staleness monitoring with circuit breakers
- Replay capability for backtesting (deterministic)

### Phase 5: Observability & Developer Experience (Weeks 10-12)

**5.1 Full OpenTelemetry Integration**
- Auto-instrumentation for FastAPI, SQLAlchemy, Redis, HTTPX
- Custom spans for: risk evaluation, order placement, fill processing, reconciliation
- Metrics: order latency, risk eval latency, fill rate, rejection rate, P&L
- Structured JSON logs with correlation IDs
- Dashboard in Grafana (or reuse existing Prometheus)

**5.2 CLI for Operators (`zksato-cli`)**
- Build with `typer` + `rich` for beautiful terminal UX
- Commands: `bot start|stop|status`, `order place|cancel|list`, `risk check|limits`, `reconcile`, `config validate|show`
- Tab completion, colored output, progress bars
- Non-interactive mode for scripting (`--output json`)
- Config validation command

**5.3 Evaluation Framework**
- Create `evals/` directory with test suites
- Strategy backtest evaluation (Sharpe, drawdown, turnover vs benchmarks)
- Risk engine property tests (invariants under adversarial conditions)
- Reconciliation accuracy tests (synthetic broker scenarios)
- Latency/performance baselines with regression detection
- CI integration: fail on regression

### Phase 6: Frontend & API Modernization (Weeks 12-14)

**6.1 API Versioning & Contracts**
- API versioning in URL (`/v1/`, `/v2/`)
- OpenAPI spec as contract (generated from code)
- Contract testing (pact or schemathesis)
- Deprecation policy with headers

**6.2 Dashboard Architecture**
- Split dashboard into: `zksato-dashboard-core` (React components), `zksato-dashboard-app` (Vite app)
- Shared component library with Storybook
- Real-time updates via SSE/WebSocket (not polling)
- TradingView chart integration as reusable component

### Phase 7: Security & Compliance Hardening (Weeks 14-16)

**7.1 Secrets & Credential Management**
- Integrate with OS keychain (keyring) for local dev
- Support for HashiCorp Vault / AWS Secrets Manager in prod
- Credential rotation without restart
- Audit log for all credential access

**7.2 Sandboxed Execution**
- Paper trading in isolated containers (network, filesystem)
- Strategy execution sandbox (no network, limited CPU/memory)
- UAT broker sandbox with traffic mirroring
- SELinux/AppArmor profiles for containers

---

## 4. Git Governance Workflow

The following workflow must be followed for all changes, using the authenticated multi-account separation:

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

**Git credentials**: Use `/home/cvsz/.git-credentials` for authentication:
```
https://cvsz:****@github.com
https://policedbc:****@github.com
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

**Non-negotiable**: 
- All commits must be GPG-signed under `cvsz` account
- PR must be created under `cvsz`, reviewed by `policedbc`, merged by `cvsz`
- Never commit, push, or merge under a different account
- Never skip GPG signing on commits

---

## 5. Success Criteria

- [ ] All features from TradingAgents framework adapted/admitted for zksato where they preserve risk invariants
- [ ] Performance: main loop throughput competitive with benchmarks (~134k risk eval/sec)
- [ ] All 10 safety invariants preserved (AGENTS.md)
- [ ] Documentation complete and up to date (FEATURE-MATRIX, INDEX, ROADMAP)
- [ ] Git governance workflow compliant (cvsz → policedcv → cvsz merge)
- [ ] pytest passes with no new failures
- [ ] ruff check/format passes
- [ ] mypy passes with no new errors
- [ ] bandit security scan: 0 critical, 0 high

---

## 6. Migration Branch Strategy

```
main (v1.x)                                                     
  │                                                             
  └── upgrade/v1-foundation (Phase 1) ──► upgrade/v1-risk (Phase 2) 
        │                                                       
        └── upgrade/v1-automation (Phase 3) ──► upgrade/v1-brokers (Phase 4)
              │                                                 
              └── upgrade/v1-observability (Phase 5) ──► upgrade/v1-frontend (Phase 6)
                    │                                         
                    └── upgrade/v1-security (Phase 7) ◄── merge with squash
```

Each phase must pass validation gates before merging. Database migrations are backward-compatible (expand-only). Canary deployment: dev → uat → prod.

---

## 7. References

- `AGENTS.md` — Safety invariants and operating contract
- `IMPLEMENTATION-PLAN.md` — Existing Phase 5 plan (adapted from anglerfish-fable5)
- `UPGRADE-PLAN.md` — gemini-cli architecture patterns adaptation
- `docs/INDEX.md` — Documentation index
- `docs/FEATURE-MATRIX.md` — Feature status matrix
- `SECURITY.md` — Security requirements and threat model
- `/home/cvsz/.git-credentials` — Git authentication credentials