# Full Monorepo Migration + Phases 2-7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate zksato from single-package `src/zksato/` to a proper UV workspace monorepo with `packages/*` and `apps/*`, and implement all remaining patterns from GEMINI-CLI-PATTERNS.md (Phases 2-7) for production-grade trading platform.

**Architecture:** Monorepo with 10 packages (zksato-core, zksato-risk, zksato-market, zksato-broker, zksato-strategy, zksato-portfolio, zksato-automation, zksato-api, zksato-cli, zksato-test-utils) and 3 apps (api, cli, worker). Each package owns a bounded domain with clear interfaces. Migration moves existing `src/zksato/` code into appropriate packages, then implements missing patterns: Policy Engine, Stable Stringify, Confirmation Bus, Scheduler+Tool Executor, Event-sourced Agent Sessions, Skill Manager, Tool Registry, Hook System, Adapter Protocol, Plugin System, Error Classification, Broker Router, Eval Framework, OpenTelemetry, Keychain Service, Rich CLI, SandboxManager, Checkpointing, A2A Protocol, Shell Execution, Memory/Context Manager.

**Tech Stack:** Python 3.11+, UV workspaces, Pydantic v2, FastAPI, SQLAlchemy 2.0, Redis, PostgreSQL, OpenTelemetry, Optuna, Hypothesis, pytest, Ruff, mypy, Typer+Rich for CLI.

**Spec:** 
- `/home/cvsz/zksato/GEMINI-CLI-PATTERNS.md` (patterns mapping)
- `/home/cvsz/zksato/ROADMAP.md` (roadmap and external gates)
- `/home/cvsz/zksato/AGENTS.md` (engineering operating contract)
- `/home/cvsz/zksato/docs/FEATURE-MATRIX.md` (capability truth table)

## Global Constraints

- Python 3.11+ required; target py311 for ruff
- All packages must have zero circular dependencies; zksato-core has zero deps on other zksato packages
- ruff check . passes with 0 errors/warnings; ruff format --check . passes
- mypy src/ packages/ apps/ passes with 0 errors (strict mode)
- pytest -m "not uat and not performance" passes (485+ tests)
- Financial invariants from AGENTS.md are non-negotiable: paper default, no autonomous live, risk engine boundary, credential isolation, fail-closed on stale feeds, idempotency, SET/TFEX separation
- All new code must have tests; property-based tests for risk/reconciliation
- GPG-signed commits required; multi-account Git governance (cvsz author → policedbc review → cvsz merge)
- Docker compose config validates; container builds succeed
- Coverage floor 70% branch

## Review Focus

1. **Credential leakage** — Secrets (broker tokens, PINs, API keys) must never appear in logs, API responses, commit history, or client-side code. Test: penetration tests in `tests/test_penetration.py` and secret scanning in CI.
2. **Fail-closed on stale feeds** — Any market data staleness >5s must reject automated orders. Test: `tests/test_financial_invariants.py` property tests for feed freshness.
3. **Idempotency across restarts** — `client_order_id` uniqueness must survive process restart. Test: `tests/test_paper_recovery.py` and `tests/test_concurrency.py` for ID uniqueness.
4. **Risk engine bypass prevention** — No code path (LLM, agent, dashboard, strategy) can place orders without RiskEngine evaluation. Test: `tests/test_risk_properties.py` and API contract tests.
5. **SET vs TFEX semantic conflation** — Equity board lots, tick rules, and TFEX margin/contract handling must remain isolated. Test: `tests/test_tfex.py` and `tests/test_market_rules.py` for domain separation.

---

### Task 1: Complete Monorepo Package Scaffolding

**Files:**
- Create: `packages/zksato-broker/pyproject.toml`
- Create: `packages/zksato-strategy/pyproject.toml`
- Create: `packages/zksato-portfolio/pyproject.toml`
- Create: `packages/zksato-automation/pyproject.toml`
- Create: `packages/zksato-api/pyproject.toml`
- Create: `packages/zksato-cli/pyproject.toml`
- Create: `packages/zksato-test-utils/pyproject.toml`
- Create: `apps/api/pyproject.toml`
- Create: `apps/cli/pyproject.toml`
- Create: `apps/worker/pyproject.toml`
- Modify: `packages/zksato-core/src/zksato_core/__init__.py` (export all public symbols)
- Modify: `packages/zksato-market/src/zksato_market/__init__.py` (export all public symbols)
- Modify: `packages/zksato-risk/src/zksato_risk/__init__.py` (export all public symbols)

**Interfaces:**
- Consumes: Root `pyproject.toml` workspace config
- Produces: Installable packages with correct dependencies and entry points

- [ ] **Step 1: Write failing tests for package imports**

```python
# tests/test_monorepo_packages.py
def test_all_packages_importable():
    import zksato_core
    import zksato_risk
    import zksato_market
    import zksato_broker
    import zksato_strategy
    import zksato_portfolio
    import zksato_automation
    import zksato_api
    import zksato_cli
    import zksato_test_utils
    assert zksato_core.__version__ == "2.0.0-dev"
```

- [ ] **Step 2: Run test to verify it fails**  
  Run: `pytest tests/test_monorepo_packages.py -v`  
  Expected: FAIL (packages not fully implemented)

- [ ] **Step 3: Create all missing pyproject.toml files** with correct dependencies:
  - zksato-broker: depends on zksato-core, zksato-market, zksato-risk
  - zksato-strategy: depends on zksato-core, zksato-risk, zksato-market
  - zksato-portfolio: depends on zksato-core, zksato-risk
  - zksato-automation: depends on zksato-core, zksato-risk, zksato-strategy, zksato-broker
  - zksato-api: depends on all packages
  - zksato-cli: depends on zksato-core, zksato-api
  - zksato-test-utils: depends on zksato-core, pytest fixtures
  - apps/api: depends on zksato-api, FastAPI, uvicorn
  - apps/cli: depends on zksato-cli, typer, rich
  - apps/worker: depends on zksato-automation, zksato-broker

- [ ] **Step 4: Create package `__init__.py` exports** for all packages

- [ ] **Step 5: Run test to verify it passes**  
  Run: `pytest tests/test_monorepo_packages.py -v`  
  Expected: PASS

- [ ] **Step 6: Commit**  
  `git add packages/*/pyproject.toml packages/*/src/*/__init__.py apps/*/pyproject.toml tests/test_monorepo_packages.py`  
  `git commit -S -m "feat(monorepo): complete package scaffolding for all 10 packages and 3 apps"`

---

### Task 2: Migrate Core Domain Types (zksato-core)

**Files:**
- Migrate: `src/zksato/types.py` → `packages/zksato-core/src/zksato_core/types.py`
- Migrate: `src/zksato/ids.py` → `packages/zksato-core/src/zksato_core/ids.py`
- Migrate: `src/zksato/money.py` → `packages/zksato-core/src/zksato_core/money.py`
- Migrate: `src/zksato/datetime.py` → `packages/zksato-core/src/zksato_core/datetime.py`
- Migrate: `src/zksato/serialization.py` → `packages/zksato-core/src/zksato_core/serialization.py`
- Migrate: `src/zksato/exceptions.py` → `packages/zksato-core/src/zksato_core/exceptions.py`
- Migrate: `src/zksato/events.py` → `packages/zksato-core/src/zksato_core/events.py`
- Migrate: `src/zksato/config.py` → `packages/zksato-core/src/zksato_core/config.py`
- Migrate: `src/zksato/utils/*` → `packages/zksato-core/src/zksato_core/utils/`
- Migrate: `src/zksato/models.py` → `packages/zksato-core/src/zksato_core/models.py`
- Migrate: `src/zksato/domain.py` → `packages/zksato-core/src/zksato_core/domain.py`
- Migrate: `src/zksato/secrets.py` → `packages/zksato-core/src/zksato_core/secrets.py`
- Create: `packages/zksato-core/src/zksato_core/observability.py` (OpenTelemetry setup)
- Create: `packages/zksato-core/src/zksato_core/telemetry.py` (TradingEvent types)
- Create: `packages/zksato-core/src/zksato_core/stable_stringify.py` (Pattern 21)

**Interfaces:**
- Consumes: None (zero dependencies on other zksato packages)
- Produces: All domain types, ULID generation, money handling, Bangkok timezone, stable JSON serialization, config base, exception hierarchy, event base classes, secret manager interface

- [ ] **Step 1: Write failing tests for migrated modules** (use existing tests as reference)
- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Copy/migrate each file from src/zksato/ to packages/zksato-core/** preserving all functionality
- [ ] **Step 4: Add stable_stringify.py with `stable_json_dumps()` and `generate_idempotency_key()`**
- [ ] **Step 5: Add observability.py with OpenTelemetry auto-instrumentation setup**
- [ ] **Step 6: Add telemetry.py with TradingEvent types and TelemetryLogger**
- [ ] **Step 7: Update secrets.py with KeychainService pattern (Pattern 11)**
- [ ] **Step 8: Run all core tests**  
  Run: `pytest packages/zksato-core/tests/ -v` (migrate tests too)  
  Expected: PASS
- [ ] **Step 9: Commit**  
  `git add packages/zksato-core/ tests/test_monorepo_packages.py`  
  `git commit -S -m "feat(core): migrate all core domain types to zksato-core package"`

---

### Task 3: Migrate Market Data Package (zksato-market)

**Files:**
- Migrate: `src/zksato/market.py` → `packages/zksato-market/src/zksato_market/feeds/base.py`
- Migrate: `src/zksato/market_settrade.py` → `packages/zksato-market/src/zksato_market/feeds/settrade.py`
- Migrate: `src/zksato/market/ccxt_feed.py` → `packages/zksato-market/src/zksato_market/feeds/ccxt.py`
- Migrate: `src/zksato/market/demo.py` → `packages/zksato-market/src/zksato_market/feeds/demo.py`
- Migrate: `src/zksato/market/prediction_feed.py` → `packages/zksato-market/src/zksato_market/feeds/prediction.py`
- Migrate: `src/zksato/scanner.py` → `packages/zksato-market/src/zksato_market/scanner.py`
- Migrate: `src/zksato/market_rules.py` → `packages/zksato-market/src/zksato_market/rules.py`
- Migrate: `src/zksato/news.py` → `packages/zksato-market/src/zksato_market/news.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/composite.py` (Pattern 23 FeedRouter)
- Create: `packages/zksato-market/src/zksato_market/feeds/protocol.py` (MarketFeed protocol)

**Interfaces:**
- Consumes: zksato-core (types, money, datetime, config, events)
- Produces: MarketFeed protocol, SettradeFeed, CCXTFeed, DemoFeed, PredictionFeed, FeedRouter, Scanner, MarketRules

- [ ] **Step 1: Write failing tests** (migrate existing market tests)
- [ ] **Step 2: Migrate all market feed implementations**
- [ ] **Step 3: Create MarketFeed protocol and FeedRouter with failover logic**
- [ ] **Step 4: Run market tests**  
  Run: `pytest tests/test_market_feeds.py tests/test_market_rules.py tests/test_scanner.py -v`  
  Expected: PASS
- [ ] **Step 5: Commit**

---

### Task 4: Migrate Risk Engine Package (zksato-risk)

**Files:**
- Migrate: `src/zksato/risk.py` → `packages/zksato-risk/src/zksato_risk/engine.py`
- Migrate: `src/zksato/protections.py` → `packages/zksato-risk/src/zksato_risk/protections.py`
- Migrate: `src/zksato/portfolio.py` → `packages/zksato-risk/src/zksato_risk/portfolio.py` (risk-related)
- Create: `packages/zksato-risk/src/zksato_risk/policies/` (Pattern 3 Policy Engine)
  - `__init__.py`, `base.py`, `registry.py`, `engine.py`
  - `notional_limit.py`, `concentration.py`, `staleness.py`, `session.py`, `spread.py`, `position.py`, `drawdown.py`, `tick_price_band.py`, `approval.py`
- Create: `packages/zksato-risk/src/zksato_risk/confirmation_bus.py` (Pattern 24)

**Interfaces:**
- Consumes: zksato-core (types, money, datetime, events, stable_stringify)
- Produces: RiskEngine, PolicyEngine, PolicyRegistry, ConfirmationBus, all risk policies, protections

- [ ] **Step 1: Write failing tests** (migrate existing risk tests)
- [ ] **Step 2: Migrate RiskEngine and protections**
- [ ] **Step 3: Implement PolicyEngine with declarative TOML config loading**
- [ ] **Step 4: Implement all 10+ risk policies as separate classes**
- [ ] **Step 5: Implement ConfirmationBus for four-eyes approval**
- [ ] **Step 6: Run risk tests**  
  Run: `pytest tests/test_risk.py tests/test_risk_advanced.py tests/test_risk_properties.py tests/test_financial_invariants.py -v`  
  Expected: PASS
- [ ] **Step 7: Commit**

---

### Task 5: Migrate Broker Package (zksato-broker)

**Files:**
- Migrate: `src/zksato/broker/base.py` → `packages/zksato-broker/src/zksato_broker/base.py`
- Migrate: `src/zksato/broker/paper.py` → `packages/zksato-broker/src/zksato_broker/paper.py`
- Migrate: `src/zksato/broker/settrade.py` → `packages/zksato-broker/src/zksato_broker/settrade.py`
- Migrate: `src/zksato/broker/ccxt.py` → `packages/zksato-broker/src/zksato_broker/ccxt.py`
- Migrate: `src/zksato/broker/prediction.py` → `packages/zksato-broker/src/zksato_broker/prediction.py`
- Create: `packages/zksato-broker/src/zksato_broker/protocol.py` (Pattern 6 BrokerAdapter protocol)
- Create: `packages/zksato-broker/src/zksato_broker/errors.py` (Pattern 22 Error Classification)
- Create: `packages/zksato-broker/src/zksato_broker/router.py` (Pattern 23 BrokerRouter)
- Create: `packages/zksato-broker/src/zksato_broker/sandbox.py` (Pattern 10 SandboxManager)

**Interfaces:**
- Consumes: zksato-core, zksato-market, zksato-risk
- Produces: BrokerAdapter protocol, PaperBroker, SettradeBroker, CCXTBroker, PredictionBroker, BrokerRouter, BrokerError classification, SandboxManager

- [ ] **Step 1: Write failing tests** (migrate existing broker tests)
- [ ] **Step 2: Migrate all broker implementations**
- [ ] **Step 3: Create BrokerAdapter protocol with capabilities**
- [ ] **Step 4: Implement BrokerError classification and retry policies**
- [ ] **Step 5: Implement BrokerRouter with failover logic**
- [ ] **Step 6: Implement SandboxManager for paper/UAT isolation**
- [ ] **Step 7: Run broker tests**  
  Run: `pytest tests/test_paper_broker_full.py tests/test_broker_ccxt.py tests/test_settrade_adapters.py tests/test_paper_matching.py -v`  
  Expected: PASS
- [ ] **Step 8: Commit**

---

### Task 6: Migrate Strategy Package (zksato-strategy)

**Files:**
- Migrate: `src/zksato/strategy.py` → `packages/zksato-strategy/src/zksato_strategy/strategies/classic.py`
- Migrate: `src/zksato/strategy_freqtrade.py` → `packages/zksato-strategy/src/zksato_strategy/strategies/freqtrade.py`
- Migrate: `src/zksato/indicators.py` → `packages/zksato-strategy/src/zksato_strategy/indicators.py`
- Migrate: `src/zksato/backtest.py` → `packages/zksato-strategy/src/zksato_strategy/backtest.py`
- Migrate: `src/zksato/backtest_enhanced.py` → `packages/zksato-strategy/src/zksato_strategy/backtest_enhanced.py`
- Migrate: `src/zksato/hyperopt.py` → `packages/zksato-strategy/src/zksato_strategy/hyperopt.py`
- Migrate: `src/zksato/pairlist.py` → `packages/zksato-strategy/src/zksato_strategy/pairlist.py`
- Migrate: `src/zksato/trailing_stop.py` → `packages/zksato-strategy/src/zksato_strategy/trailing_stop.py`
- Migrate: `src/zksato/research.py` → `packages/zksato-strategy/src/zksato_strategy/research.py`
- Migrate: `src/zksato/video_ea*.py` → `packages/zksato-strategy/src/zksato_strategy/video_ea/`
- Create: `packages/zksato-strategy/src/zksato_strategy/registry.py` (Pattern 7 Plugin Registry)
- Create: `packages/zksato-strategy/src/zksato_strategy/research/memory.py` (Pattern 17 StrategyMemory)

**Interfaces:**
- Consumes: zksato-core, zksato-risk, zksato-market
- Produces: All strategies (16+), indicators (20+), backtest engine, hyperopt, pairlists, trailing stops, video EA research, plugin registry

- [ ] **Step 1: Write failing tests** (migrate existing strategy tests)
- [ ] **Step 2: Migrate all strategy and indicator implementations**
- [ ] **Step 3: Create PluginRegistry with entry-point discovery**
- [ ] **Step 4: Implement StrategyMemory for research context persistence**
- [ ] **Step 5: Run strategy tests**  
  Run: `pytest tests/test_strategy.py tests/test_strategies_enhanced.py tests/test_indicators_full.py tests/test_indicators_advanced.py tests/test_backtest*.py tests/test_hyperopt.py -v`  
  Expected: PASS
- [ ] **Step 6: Commit**

---

### Task 7: Migrate Portfolio Package (zksato-portfolio)

**Files:**
- Migrate: `src/zksato/portfolio.py` → `packages/zksato-portfolio/src/zksato_portfolio/portfolio.py`
- Migrate: `src/zksato/reconcile.py` → `packages/zksato-portfolio/src/zksato_portfolio/reconcile.py`
- Migrate: `src/zksato/session_reconcile.py` → `packages/zksato-portfolio/src/zksato_portfolio/session_reconcile.py`
- Migrate: `src/zksato/persistence.py` → `packages/zksato-portfolio/src/zksato_portfolio/persistence.py`
- Migrate: `src/zksato/store.py` → `packages/zksato-portfolio/src/zksato_portfolio/store.py`
- Migrate: `src/zksato/outbox_delivery.py` → `packages/zksato-portfolio/src/zksato_portfolio/outbox.py`

**Interfaces:**
- Consumes: zksato-core, zksato-risk
- Produces: Portfolio management, reconciliation engine, session reconciliation, persistence layer, StateStore, outbox delivery

- [ ] **Step 1: Write failing tests** (migrate existing portfolio tests)
- [ ] **Step 2: Migrate all portfolio/reconciliation/persistence code**
- [ ] **Step 3: Run portfolio tests**  
  Run: `pytest tests/test_persistence.py tests/test_reconcile.py tests/test_reconciliation_gate.py tests/test_session_reconciliation.py tests/test_reconciliation_restart_freshness.py tests/test_outbox_delivery.py -v`  
  Expected: PASS
- [ ] **Step 4: Commit**

---

### Task 8: Migrate Automation Package (zksato-automation)

**Files:**
- Migrate: `src/zksato/automation.py` → `packages/zksato-automation/src/zksato_automation/scheduler.py`
- Migrate: `src/zksato/service.py` → `packages/zksato-automation/src/zksato_automation/service.py`
- Migrate: `src/zksato/agent_os/skills.py` → `packages/zksato-automation/src/zksato_automation/agent_os/skills.py`
- Migrate: `src/zksato/agent_os/subaccount.py` → `packages/zksato-automation/src/zksato_automation/agent_os/subaccount.py`
- Migrate: `src/zksato/agent_os/engine.py` → `packages/zksato-automation/src/zksato_automation/agent_os/engine.py`
- Migrate: `src/zksato/agent_trading/` → `packages/zksato-automation/src/zksato_automation/agent_trading/`
- Create: `packages/zksato-automation/src/zksato_automation/tools/registry.py` (Pattern 19 ToolRegistry)
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/session.py` (Pattern 5 Event-sourced AgentSession)
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/hooks.py` (Pattern 20 HookManager)
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/a2a.py` (Pattern 13 A2A Protocol)
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/state.py` (Pattern 12 CheckpointManager)

**Interfaces:**
- Consumes: zksato-core, zksato-risk, zksato-strategy, zksato-broker, zksato-portfolio
- Produces: TradingScheduler, TradingService, AgentOS (skills, subaccounts, engine, sessions), AgentTrading platform, ToolRegistry, HookManager, A2A messaging, CheckpointManager

- [ ] **Step 1: Write failing tests** (migrate existing automation tests)
- [ ] **Step 2: Migrate automation, service, agent_os, agent_trading**
- [ ] **Step 3: Implement ToolRegistry with JSON schema generation**
- [ ] **Step 4: Implement event-sourced AgentSession with event log**
- [ ] **Step 5: Implement HookManager for trading lifecycle hooks**
- [ ] **Step 6: Implement A2A protocol for inter-agent communication**
- [ ] **Step 7: Implement CheckpointManager for session resume**
- [ ] **Step 8: Run automation tests**  
  Run: `pytest tests/test_automation_controls.py tests/test_bot_enhancements.py tests/test_agent_os.py tests/test_agent_trading.py tests/test_service.py -v`  
  Expected: PASS
- [ ] **Step 9: Commit**

---

### Task 9: Migrate API Package (zksato-api)

**Files:**
- Migrate: `src/zksato/api.py` → `packages/zksato-api/src/zksato_api/main.py`
- Migrate: `src/zksato/api_freqtrade.py` → `packages/zksato-api/src/zksato_api/freqtrade.py`
- Migrate: `src/zksato/auth.py` → `packages/zksato-api/src/zksato_api/auth.py`
- Migrate: `src/zksato/security.py` → `packages/zksato-api/src/zksato_api/security.py`
- Migrate: `src/zksato/approvals.py` → `packages/zksato-api/src/zksato_api/approvals.py`
- Migrate: `src/zksato/coordination.py` → `packages/zksato-api/src/zksato_api/coordination.py`
- Migrate: `src/zksato/dashboard.py` → `packages/zksato-api/src/zksato_api/dashboard.py`
- Migrate: `src/zksato/market_terminal.py` → `packages/zksato-api/src/zksato_api/market_terminal.py`
- Migrate: `src/zksato/tradingview.py` → `packages/zksato-api/src/zksato_api/tradingview.py`
- Migrate: `src/zksato/notifications/` → `packages/zksato-api/src/zksato_api/notifications/`
- Migrate: `src/zksato/production.py` → `packages/zksato-api/src/zksato_api/production.py`
- Migrate: `src/zksato/openapi_contract.py` → `packages/zksato-api/src/zksato_api/openapi_contract.py`
- Migrate: `src/zksato/llm_clients/` → `packages/zksato-api/src/zksato_api/llm_clients/`
- Migrate: `src/zksato/prediction/` → `packages/zksato-api/src/zksato_api/prediction/`
- Migrate: `src/zksato/tfex.py` → `packages/zksato-api/src/zksato_api/tfex.py`

**Interfaces:**
- Consumes: All packages
- Produces: FastAPI app with all endpoints, auth, security, approvals, coordination, dashboard, market terminal, tradingview, notifications, prediction markets, TFEX

- [ ] **Step 1: Write failing tests** (migrate existing API tests)
- [ ] **Step 2: Migrate all API modules**
- [ ] **Step 3: Run API tests**  
  Run: `pytest tests/test_api.py tests/test_api_extended.py tests/test_auth.py tests/test_approvals.py tests/test_coordination.py tests/test_tradingview.py tests/test_telegram.py tests/test_prediction*.py tests/test_tfex*.py tests/test_production_readiness.py -v`  
  Expected: PASS
- [ ] **Step 4: Commit**

---

### Task 10: Create CLI App (apps/cli)

**Files:**
- Create: `apps/cli/src/zksato_cli/main.py` (Pattern 14 Typer+Rich CLI)
- Create: `apps/cli/src/zksato_cli/commands/` (bot, strategy, risk, broker, portfolio, agent, config)
- Create: `apps/cli/pyproject.toml` with typer, rich, zksato-cli dep

**Interfaces:**
- Consumes: zksato-cli package, zksato-api
- Produces: `zksato` CLI command with subcommands for all operations

- [ ] **Step 1: Write failing tests for CLI commands**
- [ ] **Step 2: Implement Typer+Rich CLI with all subcommands**
- [ ] **Step 3: Run CLI tests**
- [ ] **Step 4: Commit**

---

### Task 11: Create API App (apps/api)

**Files:**
- Create: `apps/api/src/main.py` (FastAPI entrypoint)
- Create: `apps/api/Dockerfile`
- Create: `apps/api/pyproject.toml` with FastAPI, uvicorn, zksato-api dep

**Interfaces:**
- Consumes: zksato-api package
- Produces: Runnable API server on port 9569

- [ ] **Step 1: Create FastAPI entrypoint that imports zksato_api.main:app**
- [ ] **Step 2: Create Dockerfile**
- [ ] **Step 3: Test API server starts**
- [ ] **Step 4: Commit**

---

### Task 12: Create Worker App (apps/worker)

**Files:**
- Create: `apps/worker/src/main.py` (Background worker entrypoint)
- Create: `apps/worker/Dockerfile`
- Create: `apps/worker/pyproject.toml` with zksato-automation, zksato-broker deps

**Interfaces:**
- Consumes: zksato-automation, zksato-broker
- Produces: Runnable background worker for automation, reconciliation, outbox delivery

- [ ] **Step 1: Create worker entrypoint**
- [ ] **Step 2: Create Dockerfile**
- [ ] **Step 3: Test worker starts**
- [ ] **Step 4: Commit**

---

### Task 13: Eval Framework (Pattern 8)

**Files:**
- Create: `evals/risk/test_invariants.py`
- Create: `evals/risk/test_latency.py`
- Create: `evals/risk/test_adversarial.py`
- Create: `evals/reconciliation/test_accuracy.py`
- Create: `evals/reconciliation/test_edge_cases.py`
- Create: `evals/reconciliation/test_restart_recovery.py`
- Create: `evals/strategy/test_backtest_fidelity.py`
- Create: `evals/strategy/test_parameter_stability.py`
- Create: `evals/strategy/test_walkforward.py`
- Create: `evals/performance/test_api_latency.py`
- Create: `evals/performance/test_throughput.py`
- Create: `evals/performance/test_memory.py`
- Create: `evals/security/test_auth.py`
- Create: `evals/security/test_secrets.py`
- Create: `evals/security/test_rbac.py`
- Create: `.github/workflows/evals.yml`

**Interfaces:**
- Consumes: All packages
- Produces: Comprehensive evaluation suites with benchmarks, regression detection

- [ ] **Step 1: Create evals directory structure**
- [ ] **Step 2: Implement all eval test files**
- [ ] **Step 3: Create GitHub Actions workflow for evals**
- [ ] **Step 4: Run evals to verify**  
  Run: `pytest evals/ -v`  
  Expected: PASS
- [ ] **Step 5: Commit**

---

### Task 14: Update Root Configuration and Documentation

**Files:**
- Modify: `pyproject.toml` (update version, ensure all packages listed)
- Modify: `docker-compose.yml` (use apps/api, apps/worker, apps/cli images)
- Modify: `docker-compose.prod.yml` (production overrides)
- Create: `config/settings.toml` (Pattern 15 TOML config)
- Create: `config/environments/dev.toml`, `uat.toml`, `prod.toml`
- Create: `config/schemas/risk-policy.schema.json`, `broker.schema.json` (auto-generated)
- Update: `README.md` (monorepo structure, new commands)
- Update: `docs/ARCHITECTURE.md` (reflect monorepo)
- Update: `docs/PROJECT-STRUCTURE.md` (new package layout)

**Interfaces:**
- Consumes: All packages and apps
- Produces: Working monorepo with proper configuration

- [ ] **Step 1: Update root pyproject.toml with correct workspace members**
- [ ] **Step 2: Create TOML configuration with layered loading (defaults → env → local)**
- [ ] **Step 3: Generate JSON schemas from Pydantic models**
- [ ] **Step 4: Update docker-compose files for new app structure**
- [ ] **Step 5: Update documentation**
- [ ] **Step 6: Run full test suite**  
  Run: `pytest -m "not uat and not performance" -v`  
  Expected: 485+ tests PASS
- [ ] **Step 7: Run ruff, mypy, docker compose config**  
  Expected: All pass
- [ ] **Step 8: Commit**

---

### Task 15: Final Validation and Multi-Account Sign-Off

**Files:**
- All modified files from Tasks 1-14

**Interfaces:**
- Consumes: Complete implementation
- Produces: Production-ready monorepo with all Phases 2-7 patterns implemented

- [ ] **Step 1: Run full validation suite**  
  `python -m pip install -e '.[dev]'`  
  `ruff check .`  
  `ruff format --check .`  
  `mypy packages/ apps/`  
  `pytest -m "not uat and not performance"`  
  `docker compose config`  
  `docker compose build`
- [ ] **Step 2: Verify all financial invariants hold**  
  `pytest tests/test_financial_invariants.py -v`
- [ ] **Step 3: Create PR as `cvsz` (author)**  
  `gh auth switch -u cvsz`  
  `git checkout -b feat/monorepo-phases2-7`  
  `git add -A`  
  `git commit -S -m "feat(monorepo): complete monorepo migration and implement Phases 2-7 patterns"`  
  `git push -u origin feat/monorepo-phases2-7`  
  `gh pr create --title "feat(monorepo): complete monorepo migration and implement Phases 2-7 patterns" --body "..."`
- [ ] **Step 4: Independent audit as `policedbc` (reviewer)**  
  `gh auth switch -u policedbc`  
  `gh pr review <pr-number> --approve -b "Independent audit: all patterns implemented, tests pass, invariants hold"`
- [ ] **Step 5: Squash merge as `cvsz` (owner)**  
  `gh auth switch -u cvsz`  
  `gh pr merge <pr-number> --squash --delete-branch`  
  `git checkout main && git pull origin main`

---

## Summary

This plan implements the complete monorepo migration and all remaining patterns from GEMINI-CLI-PATTERNS.md:

| Phase | Patterns | Tasks |
|-------|----------|-------|
| 1 | 1, 2, 15 | Tasks 1, 2, 14 |
| 2 | 3, 21, 24 | Task 4 |
| 3 | 4, 5, 18, 19, 20 | Task 8 |
| 4 | 6, 7, 22, 23 | Task 5 |
| 5 | 8, 9, 11 | Tasks 2, 13 |
| 6 | 14, 10, 12 | Tasks 10, 5, 8 |
| 7 | 13, 16, 17 | Tasks 8, 11 |

Total: ~15 tasks, each independently testable, following TDD with failing tests first. The plan preserves all existing functionality while restructuring into a proper monorepo and adding the missing architectural patterns for production-grade observability, extensibility, resilience, and operator experience.