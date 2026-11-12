# zksato Monorepo Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate zksato from monolithic FastAPI application to modular Python monorepo with UV workspaces, preserving all safety invariants and test coverage.

**Architecture:** Split `src/zksato/` into 10 domain packages under `packages/` with clear dependency hierarchy: zksato-core (foundation) → zksato-risk, zksato-market, zksato-broker, zksato-strategy, zksato-portfolio → zksato-automation, zksato-api → zksato-cli, zksato-test-utils. Three app entry points under `apps/`.

**Tech Stack:** Python 3.11+, UV workspaces, Hatchling build, Pydantic 2, FastAPI, pytest, Hypothesis, Ruff, MyPy

**Spec:** `/home/cvsz/zksato/PHASE-1-SPEC.md`

## Global Constraints

- Python 3.11+ required
- Paper mode default (`ZKSATO_TRADING_MODE=paper`)
- Autonomous live-money execution forbidden
- RiskEngine and TradingService are non-bypassable
- Broker credentials stay server-side
- All tests must pass (486+ tests)
- Ruff check and MyPy must pass
- Docker compose must build

## Review Focus

1. **Circular dependencies** - Package imports must follow strict hierarchy; no package imports from higher-level packages
2. **Configuration migration** - Old `.env` format must work alongside new TOML config
3. **API compatibility** - Existing FastAPI routes must work unchanged during transition
4. **Test isolation** - Each package's tests must run independently
5. **Import performance** - Package import time < 500ms

---

### Task 1: zksato-market Package

**Files:**
- Create: `packages/zksato-market/pyproject.toml`
- Create: `packages/zksato-market/README.md`
- Create: `packages/zksato-market/src/zksato_market/__init__.py`
- Create: `packages/zksato-market/src/zksato_market/types.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/__init__.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/base.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/settrade.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/ccxt.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/composite.py`
- Create: `packages/zksato-market/src/zksato_market/feeds/replay.py`
- Create: `packages/zksato-market/src/zksato_market/adapters/__init__.py`
- Create: `packages/zksato-market/src/zksato_market/adapters/base.py`
- Create: `packages/zksato-market/src/zksato_market/adapters/settrade.py`
- Create: `packages/zksato-market/src/zksato_market/adapters/ccxt.py`
- Create: `packages/zksato-market/src/zksato_market/reference.py`
- Create: `packages/zksato-market/src/zksato_market/calendar.py`
- Create: `packages/zksato-market/src/zksato_market/scanner.py`
- Create: `packages/zksato-market/tests/__init__.py`
- Create: `packages/zksato-market/tests/test_feeds.py`
- Create: `packages/zksato-market/tests/test_adapters.py`
- Create: `packages/zksato-market/tests/test_calendar.py`
- Create: `packages/zksato-market/tests/test_scanner.py`

**Interfaces:**
- Consumes: `zksato-core` (types, models, datetime, exceptions)
- Produces: Market data types, feed protocols, adapter protocols

- [ ] **Step 1: Write pyproject.toml with dependencies on zksato-core**
- [ ] **Step 2: Create types.py with Bar, Quote, Trade, Instrument, Session**
- [ ] **Step 3: Create feeds/base.py with Feed protocol and FeedEvent**
- [ ] **Step 4: Create feeds/settrade.py with Settrade realtime feed**
- [ ] **Step 5: Create feeds/ccxt.py with CCXT WebSocket feeds**
- [ ] **Step 6: Create feeds/composite.py with multi-feed fallback**
- [ ] **Step 7: Create feeds/replay.py with deterministic replay feed**
- [ ] **Step 8: Create adapters/base.py with MarketDataAdapter protocol**
- [ ] **Step 9: Create adapters/settrade.py with Settrade REST adapter**
- [ ] **Step 10: Create adapters/ccxt.py with CCXT REST adapter**
- [ ] **Step 11: Create reference.py with instrument reference data**
- [ ] **Step 12: Create calendar.py with market calendar**
- [ ] **Step 13: Create scanner.py with market scanner**
- [ ] **Step 14: Create __init__.py with exports**
- [ ] **Step 15: Write tests for all modules**
- [ ] **Step 16: Run tests and verify**
- [ ] **Step 17: Commit**

---

### Task 2: zksato-broker Package

**Files:**
- Create: `packages/zksato-broker/pyproject.toml`
- Create: `packages/zksato-broker/README.md`
- Create: `packages/zksato-broker/src/zksato_broker/__init__.py`
- Create: `packages/zksato-broker/src/zksato_broker/types.py`
- Create: `packages/zksato-broker/src/zksato_broker/protocol.py`
- Create: `packages/zksato-broker/src/zksato_broker/paper/__init__.py`
- Create: `packages/zksato-broker/src/zksato_broker/paper/broker.py`
- Create: `packages/zksato-broker/src/zksato_broker/paper/matching.py`
- Create: `packages/zksato-broker/src/zksato_broker/paper/state.py`
- Create: `packages/zksato-broker/src/zksato_broker/settrade/__init__.py`
- Create: `packages/zksato-broker/src/zksato_broker/settrade/broker.py`
- Create: `packages/zksato-broker/src/zksato_broker/settrade/auth.py`
- Create: `packages/zksato-broker/src/zksato_broker/settrade/mapping.py`
- Create: `packages/zksato-broker/src/zksato_broker/settrade/sandbox.py`
- Create: `packages/zksato-broker/src/zksato_broker/ccxt/__init__.py`
- Create: `packages/zksato-broker/src/zksato_broker/ccxt/broker.py`
- Create: `packages/zksato-broker/src/zksato_broker/ccxt/exchanges.py`
- Create: `packages/zksato-broker/src/zksato_broker/ccxt/sandbox.py`
- Create: `packages/zksato-broker/src/zksato_broker/registry.py`
- Create: `packages/zksato-broker/src/zksato_broker/health.py`
- Create: `packages/zksato-broker/src/zksato_broker/reconciliation.py`
- Create: `packages/zksato-broker/tests/__init__.py`
- Create: `packages/zksato-broker/tests/test_protocol.py`
- Create: `packages/zksato-broker/tests/test_paper/`
- Create: `packages/zksato-broker/tests/test_settrade/`
- Create: `packages/zksato-broker/tests/test_ccxt/`
- Create: `packages/zksato-broker/tests/test_reconciliation.py`

**Interfaces:**
- Consumes: `zksato-core`, `zksato-market`
- Produces: BrokerAdapter protocol, PaperBroker, SettradeBroker, CCXTBroker

- [ ] **Step 1: Write pyproject.toml with dependencies**
- [ ] **Step 2: Create types.py with Order, Fill, Position, Account, Capability**
- [ ] **Step 3: Create protocol.py with BrokerAdapter protocol**
- [ ] **Step 4: Create paper/broker.py with PaperBroker implementation**
- [ ] **Step 5: Create paper/matching.py with matching engine**
- [ ] **Step 6: Create paper/state.py with paper state management**
- [ ] **Step 7: Create settrade/broker.py with SettradeBroker**
- [ ] **Step 8: Create settrade/auth.py with authentication**
- [ ] **Step 9: Create settrade/mapping.py with order/position mapping**
- [ ] **Step 10: Create settrade/sandbox.py with sandbox mode**
- [ ] **Step 11: Create ccxt/broker.py with CCXTBroker**
- [ ] **Step 12: Create ccxt/exchanges.py with exchange config**
- [ ] **Step 13: Create registry.py, health.py, reconciliation.py**
- [ ] **Step 14: Create __init__.py with exports**
- [ ] **Step 15: Write tests**
- [ ] **Step 16: Run tests and verify**
- [ ] **Step 17: Commit**

---

### Task 3: zksato-strategy Package

**Files:**
- Create: `packages/zksato-strategy/pyproject.toml`
- Create: `packages/zksato-strategy/README.md`
- Create: `packages/zksato-strategy/src/zksato_strategy/__init__.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/types.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/base.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/registry.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/__init__.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/trend.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/mean_reversion.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/momentum.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/volatility.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/statistical.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/tfex.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/catalog/ml.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/__init__.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/base.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/trend.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/momentum.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/volatility.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/indicators/volume.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/__init__.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/engine.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/cost_model.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/metrics.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/walkforward.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/backtest/report.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/optimization/__init__.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/optimization/hyperopt.py`
- Create: `packages/zksato-strategy/src/zksato_strategy/optimization/parameter_space.py`
- Create: `packages/zksato-strategy/tests/__init__.py`
- Create: `packages/zksato-strategy/tests/test_base.py`
- Create: `packages/zksato-strategy/tests/test_catalog/`
- Create: `packages/zksato-strategy/tests/test_indicators/`
- Create: `packages/zksato-strategy/tests/test_backtest/`
- Create: `packages/zksato-strategy/tests/test_optimization/`

**Interfaces:**
- Consumes: `zksato-core`, `zksato-market`, `zksato-risk`
- Produces: Strategy framework, indicators, backtesting, optimization

---

### Task 4: zksato-portfolio Package

**Files:**
- Create: `packages/zksato-portfolio/pyproject.toml`
- Create: `packages/zksato-portfolio/README.md`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/__init__.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/types.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/portfolio.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/positions.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/pnl.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/allocation.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/accounting.py`
- Create: `packages/zksato-portfolio/src/zksato_portfolio/snapshots.py`
- Create: `packages/zksato-portfolio/tests/__init__.py`
- Create: `packages/zksato-portfolio/tests/test_portfolio.py`
- Create: `packages/zksato-portfolio/tests/test_positions.py`
- Create: `packages/zksato-portfolio/tests/test_pnl.py`
- Create: `packages/zksato-portfolio/tests/test_allocation.py`
- Create: `packages/zksato-portfolio/tests/test_accounting.py`

**Interfaces:**
- Consumes: `zksato-core`, `zksato-broker`
- Produces: Portfolio management, position tracking, P&L, accounting

---

### Task 5: zksato-automation Package

**Files:**
- Create: `packages/zksato-automation/pyproject.toml`
- Create: `packages/zksato-automation/README.md`
- Create: `packages/zksato-automation/src/zksato_automation/__init__.py`
- Create: `packages/zksato-automation/src/zksato_automation/types.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/__init__.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/scheduler.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/executor.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/state.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/hooks.py`
- Create: `packages/zksato-automation/src/zksato_automation/scheduler/parallel.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/__init__.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/registry.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/market.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/orders.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/risk.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/portfolio.py`
- Create: `packages/zksato-automation/src/zksato_automation/tools/reconciliation.py`
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/__init__.py`
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/session.py`
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/subaccounts.py`
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/skills.py`
- Create: `packages/zksato-automation/src/zksato_automation/agent_os/a2a.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/__init__.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/base.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/reconciliation.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/alerts.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/market_data.py`
- Create: `packages/zksato-automation/src/zksato_automation/workers/strategy_eval.py`
- Create: `packages/zksato-automation/tests/__init__.py`
- Create: `packages/zksato-automation/tests/test_scheduler/`
- Create: `packages/zksato-automation/tests/test_tools/`
- Create: `packages/zksato-automation/tests/test_agent_os/`
- Create: `packages/zksato-automation/tests/test_workers/`

**Interfaces:**
- Consumes: `zksato-core`, `zksato-risk`, `zksato-broker`, `zksato-portfolio`
- Produces: Agent scheduler, tool registry, agent OS, background workers

---

### Task 6: zksato-api Package

**Files:**
- Create: `packages/zksato-api/pyproject.toml`
- Create: `packages/zksato-api/README.md`
- Create: `packages/zksato-api/src/zksato_api/__init__.py`
- Create: `packages/zksato-api/src/zksato_api/main.py`
- Create: `packages/zksato-api/src/zksato_api/routes/__init__.py`
- Create: `packages/zksato-api/src/zksato_api/routes/health.py`
- Create: `packages/zksato-api/src/zksato_api/routes/auth.py`
- Create: `packages/zksato-api/src/zksato_api/routes/market.py`
- Create: `packages/zksato-api/src/zksato_api/routes/orders.py`
- Create: `packages/zksato-api/src/zksato_api/routes/risk.py`
- Create: `packages/zksato-api/src/zksato_api/routes/portfolio.py`
- Create: `packages/zksato-api/src/zksato_api/routes/automation.py`
- Create: `packages/zksato-api/src/zksato_api/routes/backtest.py`
- Create: `packages/zksato-api/src/zksato_api/routes/prediction.py`
- Create: `packages/zksato-api/src/zksato_api/routes/tfex.py`
- Create: `packages/zksato-api/src/zksato_api/routes/freqtrade.py`
- Create: `packages/zksato-api/src/zksato_api/routes/webhooks.py`
- Create: `packages/zksato-api/src/zksato_api/routes/admin.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/__init__.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/auth.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/cors.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/csrf.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/request_id.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/rate_limit.py`
- Create: `packages/zksato-api/src/zksato_api/middleware/security_headers.py`
- Create: `packages/zksato-api/src/zksato_api/dependencies.py`
- Create: `packages/zksato-api/src/zksato_api/openapi.py`
- Create: `packages/zksato-api/src/zksato_api/lifespan.py`
- Create: `packages/zksato-api/tests/__init__.py`
- Create: `packages/zksato-api/tests/test_health.py`
- Create: `packages/zksato-api/tests/test_auth.py`
- Create: `packages/zksato-api/tests/test_routes/`
- Create: `packages/zksato-api/tests/test_middleware.py`
- Create: `packages/zksato-api/tests/test_openapi_contract.py`

**Interfaces:**
- Consumes: All domain packages
- Produces: FastAPI application factory, routes, middleware

---

### Task 7: zksato-cli Package

**Files:**
- Create: `packages/zksato-cli/pyproject.toml`
- Create: `packages/zksato-cli/README.md`
- Create: `packages/zksato-cli/src/zksato_cli/__init__.py`
- Create: `packages/zksato-cli/src/zksato_cli/main.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/__init__.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/bot.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/order.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/risk.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/portfolio.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/reconcile.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/config.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/market.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/strategy.py`
- Create: `packages/zksato-cli/src/zksato_cli/commands/admin.py`
- Create: `packages/zksato-cli/src/zksato_cli/output.py`
- Create: `packages/zksato-cli/src/zksato_cli/context.py`
- Create: `packages/zksato-cli/src/zksato_cli/completion.py`
- Create: `packages/zksato-cli/tests/__init__.py`
- Create: `packages/zksato-cli/tests/test_commands/`
- Create: `packages/zksato-cli/tests/test_output.py`

**Interfaces:**
- Consumes: `zksato-core`, `zksato-api` (as client)
- Produces: Typer CLI application

---

### Task 8: zksato-test-utils Package

**Files:**
- Create: `packages/zksato-test-utils/pyproject.toml`
- Create: `packages/zksato-test-utils/README.md`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/__init__.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/__init__.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/orders.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/fills.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/positions.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/accounts.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/market.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/strategies.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/fixtures/risk.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/harnesses/__init__.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/harnesses/broker.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/harnesses/risk.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/harnesses/strategy.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/harnesses/api.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/matchers.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/property.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/async_utils.py`
- Create: `packages/zksato-test-utils/src/zksato_test_utils/docker.py`
- Create: `packages/zksato-test-utils/tests/__init__.py`
- Create: `packages/zksato-test-utils/tests/test_factories.py`

**Interfaces:**
- Consumes: `zksato-core`
- Produces: Test fixtures, harnesses, property strategies

---

### Task 9: App Entry Points

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/zksato_api_app/__init__.py`
- Create: `apps/api/src/zksato_api_app/main.py`
- Create: `apps/api/src/zksato_api_app/config.py`
- Create: `apps/api/tests/test_main.py`
- Create: `apps/cli/pyproject.toml`
- Create: `apps/cli/src/zksato_cli_app/__init__.py`
- Create: `apps/cli/src/zksato_cli_app/main.py`
- Create: `apps/cli/tests/test_main.py`
- Create: `apps/worker/pyproject.toml`
- Create: `apps/worker/src/zksato_worker/__init__.py`
- Create: `apps/worker/src/zksato_worker/main.py`
- Create: `apps/worker/src/zksato_worker/reconciliation.py`
- Create: `apps/worker/src/zksato_worker/alerts.py`
- Create: `apps/worker/src/zksato_worker/market_data.py`
- Create: `apps/worker/src/zksato_worker/strategy_eval.py`
- Create: `apps/worker/tests/test_workers.py`

**Interfaces:**
- Consumes: All packages
- Produces: Executable entry points

---

### Task 10: Configuration System & Integration Tests

**Files:**
- Create: `config/settings.toml`
- Create: `config/environments/dev.toml`
- Create: `config/environments/test.toml`
- Create: `config/environments/uat.toml`
- Create: `config/environments/prod.toml`
- Create: `config/policies/risk/trading.toml`
- Create: `config/policies/risk/approval.toml`
- Create: `config/policies/risk/limits.toml`
- Create: `config/policies/broker/paper.toml`
- Create: `config/policies/broker/settrade.toml`
- Create: `config/policies/broker/ccxt.toml`
- Create: `config/policies/strategy/default.toml`
- Create: `config/policies/strategy/catalog.toml`
- Modify: `pyproject.toml` (root) - update for new structure
- Create: `tests/integration/test_cross_package.py`

**Interfaces:**
- Consumes: All packages
- Produces: Working monorepo with configuration

- [ ] **Step 1: Create config files**
- [ ] **Step 2: Update root pyproject.toml**
- [ ] **Step 3: Run full test suite**
- [ ] **Step 4: Run linting and type checking**
- [ ] **Step 5: Test Docker build**
- [ ] **Step 6: Verify all entry points work**
- [ ] **Step 7: Commit**

---

## Self-Review Checklist

- [x] Spec coverage: All packages from PHASE-1-SPEC.md are covered
- [x] Step scan: Each task has clear, testable steps
- [x] Type consistency: Package hierarchy follows dependency graph
- [x] Review focus: Top 5 failure modes identified
- [x] Proportion: Plan is appropriate size for spec