# Phase 1 Specification: Monorepo Migration & Core Domain Extraction

## Objective

Transform zksato from a single-package FastAPI application into a modular Python monorepo using UV workspaces, with clean domain boundaries and shared test utilities.

---

## 1. Root Workspace Configuration

### pyproject.toml (Root)
```toml
[project]
name = "zksato-workspace"
version = "2.0.0-dev"
description = "zksato modular monorepo workspace"
requires-python = ">=3.11"
dependencies = []

[tool.uv.workspace]
members = [
    "packages/*",
    "apps/*",
]

[tool.uv.sources]
zksato-core = { workspace = true }
zksato-risk = { workspace = true }
zksato-market = { workspace = true }
zksato-broker = { workspace = true }
zksato-strategy = { workspace = true }
zksato-portfolio = { workspace = true }
zksato-automation = { workspace = true }
zksato-api = { workspace = true }
zksato-cli = { workspace = true }
zksato-test-utils = { workspace = true }

[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "UP", "B", "SIM", "ANN", "ARG", "PTH", "ERA", "PL", "TRY", "TID", "NPY", "PERF", "RUF", "UP"]
ignore = ["ANN101", "ANN102", "ARG001", "ARG002", "PTH118", "ERA001", "PLW0603", "TRY003", "TID252", "NPY002"]
[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
strict = true
warn_redundant_casts = true
warn_unreachable = true
warn_unused_configs = true
warn_unused_ignores = true
show_error_codes = true
pretty = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
enable_error_code = ["ignore-without-code"]

[tool.pytest.ini_options]
addopts = "-q --strict-markers --strict-config"
pythonpath = ["."]
testpaths = ["tests", "packages/*/tests", "apps/*/tests"]
asyncio_mode = "auto"
markers = [
    "performance: load/performance tests excluded from normal CI",
    "uat: requires broker-provided UAT credentials",
    "integration: requires external services",
    "eval: evaluation/benchmark tests",
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]

[tool.coverage.run]
branch = true
source = ["packages", "apps"]
parallel = true

[tool.coverage.report]
fail_under = 70
show_missing = true
skip_covered = true
```

---

## 2. Package Structure

### 2.1 zksato-core (Foundation)
```
packages/zksato-core/
├── pyproject.toml
├── src/
│   └── zksato_core/
│       ├── __init__.py
│       ├── types.py              # Shared enums, type aliases, constants
│       ├── ids.py                # ULID, idempotency keys, correlation IDs
│       ├── money.py              # Decimal money handling, currency
│       ├── datetime.py           # Bangkok timezone, market sessions
│       ├── serialization.py      # JSON/msgpack serialization, pydantic helpers
│       ├── exceptions.py         # Domain exceptions hierarchy
│       ├── events.py             # Event base classes, event store interface
│       ├── config.py             # Config base classes, validation
│       └── utils/
│           ├── __init__.py
│           ├── collections.py
│           ├── functional.py
│           └── async_utils.py
└── tests/
    ├── __init__.py
    ├── test_ids.py
    ├── test_money.py
    ├── test_datetime.py
    ├── test_serialization.py
    └── test_exceptions.py
```

**pyproject.toml**:
```toml
[project]
name = "zksato-core"
version = "2.0.0-dev"
description = "zksato core domain types and utilities"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.10,<3.0",
    "pydantic-settings>=2.7,<3.0",
    "ulid-py>=1.0,<2.0",
    "python-dateutil>=2.9,<3.0",
    "pendulum>=3.0,<4.0",  # For Bangkok timezone
]
readme = "README.md"
license = { text = "MIT" }

[project.optional-dependencies]
dev = [
    "pytest>=9.0,<10.0",
    "pytest-asyncio>=1.4,<2.0",
    "hypothesis>=6.160,<7.0",
    "ruff==0.16.6",
]

[tool.hatch.build.targets.wheel]
packages = ["src/zksato_core"]
```

### 2.2 zksato-risk (Risk Engine & Policies)
```
packages/zksato-risk/
├── pyproject.toml
├── src/
│   └── zksato_risk/
│       ├── __init__.py
│       ├── engine.py           # RiskEngine, RiskContext, RiskResult
│       ├── policies/
│       │   ├── __init__.py
│       │   ├── base.py         # Policy, PolicyDecision, PolicyEngine
│       │   ├── registry.py     # PolicyRegistry, policy discovery
│       │   ├── loader.py       # TOML/YAML policy loader with validation
│       │   ├── trading.py      # Built-in trading policies
│       │   └── approval.py     # Approval modes, four-eyes
│       ├── checks/
│       │   ├── __init__.py
│       │   ├── base.py         # RiskCheck protocol
│       │   ├── position.py     # Position limits, concentration
│       │   ├── notional.py     # Notional, daily loss, drawdown
│       │   ├── market.py       # Feed freshness, spread, session
│       │   └── portfolio.py    # VaR, CVaR, correlation
│       ├── models.py           # Risk models, limit definitions
│       └── metrics.py          # Risk evaluation metrics
└── tests/
    ├── __init__.py
    ├── test_engine.py
    ├── test_policies/
    │   ├── test_base.py
    │   ├── test_trading.py
    │   └── test_approval.py
    ├── test_checks/
    │   ├── test_position.py
    │   ├── test_notional.py
    │   ├── test_market.py
    │   └── test_portfolio.py
    └── test_property_based.py  # Hypothesis tests for invariants
```

### 2.3 zksato-market (Market Data)
```
packages/zksato-market/
├── pyproject.toml
├── src/
│   └── zksato_market/
│       ├── __init__.py
│       ├── types.py            # Bar, Quote, Trade, Instrument, Session
│       ├── feeds/
│       │   ├── __init__.py
│       │   ├── base.py         # Feed protocol, FeedEvent
│       │   ├── settrade.py     # Settrade realtime feed
│       │   ├── ccxt.py         # CCXT WebSocket feeds
│       │   ├── composite.py    # Multi-feed with fallback
│       │   └── replay.py       # Deterministic replay feed
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py         # MarketDataAdapter protocol
│       │   ├── settrade.py     # Settrade REST adapter
│       │   └── ccxt.py         # CCXT REST adapter
│       ├── reference.py        # Instrument reference data, tick sizes
│       ├── calendar.py         # Market calendar, sessions, holidays
│       └── scanner.py          # Market scanner, screening
└── tests/
    ├── __init__.py
    ├── test_types.py
    ├── test_feeds/
    ├── test_adapters/
    ├── test_calendar.py
    └── test_scanner.py
```

### 2.4 zksato-broker (Broker Adapters)
```
packages/zksato-broker/
├── pyproject.toml
├── src/
│   └── zksato_broker/
│       ├── __init__.py
│       ├── types.py            # Order, Fill, Position, Account, Capability
│       ├── protocol.py         # BrokerAdapter protocol, Capability enum
│       ├── paper/
│       │   ├── __init__.py
│       │   ├── broker.py       # PaperBroker implementation
│       │   ├── matching.py     # Matching engine (resting limits, partial fills)
│       │   └── state.py        # Paper state (cash, holdings, orders)
│       ├── settrade/
│       │   ├── __init__.py
│       │   ├── broker.py       # SettradeBroker
│       │   ├── auth.py         # Settrade authentication
│       │   ├── mapping.py      # Order/position mapping
│       │   └── sandbox.py      # Sandbox mode
│       ├── ccxt/
│       │   ├── __init__.py
│       │   ├── broker.py       # CCXTBroker (multi-exchange)
│       │   ├── exchanges.py    # Exchange-specific config
│       │   └── sandbox.py      # Sandbox/testnet mode
│       ├── registry.py         # Adapter registry, discovery
│       ├── health.py           # Health checks, capability reporting
│       └── reconciliation.py   # Reconciliation logic
└── tests/
    ├── __init__.py
    ├── test_protocol.py
    ├── test_paper/
    │   ├── test_broker.py
    │   ├── test_matching.py
    │   └── test_state.py
    ├── test_settrade/
    ├── test_ccxt/
    └── test_reconciliation.py
```

### 2.5 zksato-strategy (Strategy Framework)
```
packages/zksato-strategy/
├── pyproject.toml
├── src/
│   └── zksato_strategy/
│       ├── __init__.py
│       ├── types.py            # Signal, StrategyConfig, ParameterSpace
│       ├── base.py             # Strategy protocol, base classes
│       ├── registry.py         # Strategy registry, discovery
│       ├── catalog/
│       │   ├── __init__.py
│       │   ├── trend.py        # EMA, SMA, MACD, breakout
│       │   ├── mean_reversion.py  # RSI, Bollinger, stochastic
│       │   ├── momentum.py
│       │   ├── volatility.py   # ATR channel, VWAP
│       │   ├── statistical.py  # Stat arb, z-score
│       │   ├── tfex.py         # Calendar spread, basis
│       │   └── ml.py           # LLM sentiment, XGBoost
│       ├── indicators/
│       │   ├── __init__.py
│       │   ├── base.py         # Indicator protocol
│       │   ├── trend.py        # SMA, EMA, MACD, ADX
│       │   ├── momentum.py     # RSI, ROC, stochastic, Williams %R
│       │   ├── volatility.py   # ATR, Bollinger, realized vol
│       │   └── volume.py       # VWAP, OBV
│       ├── backtest/
│       │   ├── __init__.py
│       │   ├── engine.py       # BacktestEngine
│       │   ├── cost_model.py   # Commission, slippage, spread
│       │   ├── metrics.py      # Sharpe, drawdown, win rate, etc.
│       │   ├── walkforward.py  # Walk-forward/OOS
│       │   └── report.py       # BacktestReport
│       └── optimization/
│           ├── __init__.py
│           ├── hyperopt.py     # Optuna integration
│           └── parameter_space.py
└── tests/
    ├── __init__.py
    ├── test_base.py
    ├── test_catalog/
    ├── test_indicators/
    ├── test_backtest/
    └── test_optimization/
```

### 2.6 zksato-portfolio (Portfolio & Positions)
```
packages/zksato-portfolio/
├── pyproject.toml
├── src/
│   └── zksato_portfolio/
│       ├── __init__.py
│       ├── types.py            # Portfolio, Position, PnL, Allocation
│       ├── portfolio.py        # Portfolio management
│       ├── positions.py        # Position tracking, aggregation
│       ├── pnl.py              # Realized/unrealized P&L
│       ├── allocation.py       # Target allocation, rebalancing
│       ├── accounting.py       # Tax lots, cost basis, wash sales
│       └── snapshots.py        # Account snapshots, history
└── tests/
    ├── __init__.py
    ├── test_portfolio.py
    ├── test_positions.py
    ├── test_pnl.py
    ├── test_allocation.py
    └── test_accounting.py
```

### 2.7 zksato-automation (Orchestration & Agent OS)
```
packages/zksato-automation/
├── pyproject.toml
├── src/
│   └── zksato_automation/
│       ├── __init__.py
│       ├── types.py            # Tool, ToolContext, ToolResult, AgentEvent
│       ├── scheduler/
│       │   ├── __init__.py
│       │   ├── scheduler.py    # AgentScheduler
│       │   ├── executor.py     # ToolExecutor with hooks
│       │   ├── state.py        # SessionState, Checkpoint
│       │   ├── hooks.py        # Pre/Post hooks, error handling
│       │   └── parallel.py     # Parallel execution, semaphores
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py     # ToolRegistry
│       │   ├── market.py       # Market data tools
│       │   ├── orders.py       # Order management tools
│       │   ├── risk.py         # Risk check tools
│       │   ├── portfolio.py    # Portfolio query tools
│       │   └── reconciliation.py
│       ├── agent_os/
│       │   ├── __init__.py
│       │   ├── session.py      # AgentSession (event-sourced)
│       │   ├── subaccounts.py  # SubAccount, quotas, isolation
│       │   ├── skills.py       # Skill registry, built-in skills
│       │   └── a2a.py          # Agent-to-Agent protocol
│       └── workers/
│           ├── __init__.py
│           ├── base.py         # Worker base class
│           ├── reconciliation.py
│           ├── alerts.py
│           ├── market_data.py
│           └── strategy_eval.py
└── tests/
    ├── __init__.py
    ├── test_scheduler/
    ├── test_tools/
    ├── test_agent_os/
    └── test_workers/
```

### 2.8 zksato-api (FastAPI Application)
```
packages/zksato-api/
├── pyproject.toml
├── src/
│   └── zksato_api/
│       ├── __init__.py
│       ├── main.py             # FastAPI app factory
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── health.py       # /livez, /readyz, /health, /metrics
│       │   ├── auth.py         # /auth/*
│       │   ├── market.py       # /market/*
│       │   ├── orders.py       # /orders/*
│       │   ├── risk.py         # /risk/*
│       │   ├── portfolio.py    # /portfolio/*
│       │   ├── automation.py   # /bot/*, /agent-os/*
│       │   ├── backtest.py     # /backtest/*
│       │   ├── prediction.py   # /prediction/*
│       │   ├── tfex.py         # /tfex/*
│       │   ├── freqtrade.py    # /freqtrade/*
│       │   ├── webhooks.py     # /webhooks/*
│       │   └── admin.py        # /admin/*
│       ├── middleware/
│       │   ├── __init__.py
│       │   ├── auth.py         # API key, session, RBAC
│       │   ├── cors.py
│       │   ├── csrf.py
│       │   ├── request_id.py   # X-Request-ID propagation
│       │   ├── rate_limit.py
│       │   └── security_headers.py
│       ├── dependencies.py     # FastAPI dependencies
│       ├── openapi.py          # OpenAPI customization
│       └── lifespan.py         # Startup/shutdown
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_auth.py
    ├── test_routes/
    ├── test_middleware.py
    └── test_openapi_contract.py
```

### 2.9 zksato-cli (Operator CLI)
```
packages/zksato-cli/
├── pyproject.toml
├── src/
│   └── zksato_cli/
│       ├── __init__.py
│       ├── main.py             # Typer app
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── bot.py          # bot start|stop|status|tick
│       │   ├── order.py        # order place|cancel|list|detail
│       │   ├── risk.py         # risk check|limits|evaluate
│       │   ├── portfolio.py    # portfolio show|positions|pnl
│       │   ├── reconcile.py    # reconcile run|status|resolve
│       │   ├── config.py       # config validate|show|edit
│       │   ├── market.py       # market quote|bars|scan
│       │   ├── strategy.py     # strategy list|run|backtest|optimize
│       │   └── admin.py        # admin api-keys|users|secrets
│       ├── output.py           # Rich output formatting (table, json, yaml)
│       ├── context.py          # CLI context (config, client, auth)
│       └── completion.py       # Shell completion
└── tests/
    ├── __init__.py
    ├── test_commands/
    └── test_output.py
```

### 2.10 zksato-test-utils (Shared Test Infrastructure)
```
packages/zksato-test-utils/
├── pyproject.toml
├── src/
│   └── zksato_test_utils/
│       ├── __init__.py
│       ├── fixtures/
│       │   ├── __init__.py
│       │   ├── orders.py       # Order factories
│       │   ├── fills.py        # Fill factories
│       │   ├── positions.py    # Position factories
│       │   ├── accounts.py     # Account factories
│       │   ├── market.py       # Bar/Quote/Trade factories
│       │   ├── strategies.py   # Strategy config factories
│       │   └── risk.py         # Risk context factories
│       ├── harnesses/
│       │   ├── __init__.py
│       │   ├── broker.py       # PaperBrokerHarness
│       │   ├── risk.py         # RiskEngineHarness
│       │   ├── strategy.py     # StrategyHarness
│       │   └── api.py          # TestClientHarness
│       ├── matchers.py         # Custom pytest matchers
│       ├── property.py         # Hypothesis strategies
│       ├── async_utils.py      # Async test helpers
│       └── docker.py           # Testcontainers helpers
└── tests/
    ├── __init__.py
    └── test_factories.py
```

---

## 3. Application Entry Points

### 3.1 API Server (apps/api)
```
apps/api/
├── pyproject.toml
├── src/
│   └── zksato_api_app/
│       ├── __init__.py
│       ├── main.py             # Entry point: uvicorn zksato_api_app.main:app
│       └── config.py           # App-specific config loading
└── tests/
    └── test_main.py
```

**main.py**:
```python
"""zksato API server entry point."""

from zksato_api import create_app
from zksato_api.config import load_config

config = load_config()
app = create_app(config)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9569)
```

### 3.2 CLI (apps/cli)
```
apps/cli/
├── pyproject.toml
├── src/
│   └── zksato_cli_app/
│       ├── __init__.py
│       └── main.py             # Entry point: zksato
└── tests/
    └── test_main.py
```

### 3.3 Workers (apps/worker)
```
apps/worker/
├── pyproject.toml
├── src/
│   └── zksato_worker/
│       ├── __init__.py
│       ├── main.py             # Entry point for all workers
│       ├── reconciliation.py   # ReconciliationWorker
│       ├── alerts.py           # AlertWorker
│       ├── market_data.py      # MarketDataWorker
│       └── strategy_eval.py    # StrategyEvalWorker
└── tests/
    └── test_workers.py
```

---

## 4. Configuration System

### 4.1 Config File Structure
```
config/
├── settings.toml                    # Main config (committed)
├── settings.local.toml              # Local overrides (gitignored)
├── environments/
│   ├── dev.toml
│   ├── test.toml
│   ├── uat.toml
│   └── prod.toml
└── policies/
    ├── risk/
    │   ├── trading.toml
    │   ├── approval.toml
    │   └── limits.toml
    ├── broker/
    │   ├── paper.toml
    │   ├── settrade.toml
    │   └── ccxt.toml
    └── strategy/
        ├── default.toml
        └── catalog.toml
```

### 4.2 Config Loading (zksato-core)
```python
# packages/zksato-core/src/zksato_core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import tomllib


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZKSATO_",
        env_nested_delimiter="__",
        extra="ignore",
        toml_file=Path("config/settings.toml"),
    )

    # Loaded from TOML, overridden by env
    trading_mode: str = "paper"
    database_url: str
    redis_url: str
    log_level: str = "INFO"

    @classmethod
    def load(cls, env: str | None = None) -> "BaseConfig":
        """Load config with environment-specific overrides."""
        config_files = [Path("config/settings.toml")]
        if env:
            config_files.append(Path(f"config/environments/{env}.toml"))
        config_files.append(Path("config/settings.local.toml"))

        # Merge TOML files, then apply env vars
        data = {}
        for f in config_files:
            if f.exists():
                with f.open("rb") as fp:
                    data.update(tomllib.load(fp))
        return cls(**data)
```

---

## 5. Migration Steps

### Step 1: Create Root Workspace (Day 1)
```bash
# 1. Initialize UV workspace
uv init --workspace zksato-workspace
cd zksato-workspace

# 2. Create package directories
mkdir -p packages/{zksato-core,zksato-risk,zksato-market,zksato-broker,zksato-strategy,zksato-portfolio,zksato-automation,zksato-api,zksato-cli,zksato-test-utils}
mkdir -p apps/{api,cli,worker}
mkdir -p config/{environments,policies/{risk,broker,strategy}}

# 3. Create root pyproject.toml (from spec above)
# 4. Create each package's pyproject.toml and src structure
```

### Step 2: Extract Core Domain (Days 2-3)
```bash
# Move and refactor src/zksato/domain.py → packages/zksato-core/src/zksato_core/
# Split into: types.py, ids.py, money.py, datetime.py, serialization.py, exceptions.py, events.py, config.py

# Move src/zksato/config.py → packages/zksato-core/src/zksato_core/config.py (refactor)
# Move src/zksato/secrets.py → packages/zksato-core/src/zksato_core/secrets.py
```

### Step 3: Extract Risk Engine (Days 4-5)
```bash
# Move src/zksato/risk.py → packages/zksato-risk/src/zksato_risk/engine.py
# Create policy framework (base.py, registry.py, loader.py)
# Create checks modules
# Move tests/test_risk*.py → packages/zksato-risk/tests/
```

### Step 4: Extract Market & Broker (Days 6-8)
```bash
# Market: src/zksato/market*.py → packages/zksato-market/
# Broker: src/zksato/broker/ → packages/zksato-broker/
# Move corresponding tests
```

### Step 5: Extract Strategy & Portfolio (Days 9-11)
```bash
# Strategy: src/zksato/strategy*.py, indicators.py, backtest.py → packages/zksato-strategy/
# Portfolio: src/zksato/portfolio.py → packages/zksato-portfolio/
# Prediction: src/zksato/prediction/ → packages/zksato-strategy/prediction/ (or separate package)
```

### Step 6: Extract Automation & API (Days 12-14)
```bash
# Automation: src/zksato/automation.py, coordination.py, approvals.py, agent_trading/ → packages/zksato-automation/
# API: src/zksato/api.py, api_freqtrade.py, dashboard.py, auth.py, openapi_contract.py → packages/zksato-api/
# CLI: Create new zksato-cli package with Typer
```

### Step 7: Create Test Utilities (Day 15)
```bash
# Consolidate test fixtures from tests/ → packages/zksato-test-utils/
# Create harnesses for common test patterns
```

### Step 8: Create App Entry Points (Day 16)
```bash
# Create apps/api, apps/cli, apps/worker
# Update docker-compose.yml to use new entry points
```

### Step 9: Update CI/CD & Documentation (Days 17-18)
```bash
# Update GitHub Actions workflows
# Update README.md, CONTRIBUTING.md
# Update AGENTS.md with new package ownership map
# Create migration guide for developers
```

### Step 10: Validation & Polish (Days 19-21)
```bash
# Run full test suite
uv run pytest

# Run linting and type checking
uv run ruff check .
uv run mypy .

# Test Docker build
docker compose build

# Verify all entry points work
uv run zksato --help
uv run uvicorn zksato_api_app.main:app --port 9569
```

---

## 6. Backward Compatibility

### 6.1 Import Aliases (Transition Period)
```python
# packages/zksato-core/src/zksato_core/__init__.py
# Re-export old module paths for gradual migration
from zksato_core.types import *  # noqa
from zksato_core.ids import *    # noqa
# ...

# In root __init__.py (for scripts that import zksato directly)
import zksato_core as zksato
import zksato_risk as zksato.risk
import zksato_market as zksato.market
# ... etc

sys.modules["zksato"] = zksato
sys.modules["zksato.risk"] = zksato_risk
# ...
```

### 6.2 Config Compatibility
- Support old `.env` format alongside new TOML
- Deprecation warnings for old config keys
- Migration script: `zksato config migrate`

---

## 7. Verification Checklist

### Package Independence
- [ ] Each package installs independently: `uv pip install -e packages/zksato-core`
- [ ] No circular dependencies between packages
- [ ] `zksato-core` has zero zksato dependencies
- [ ] `zksato-risk` depends only on `zksato-core`
- [ ] `zksato-market` depends only on `zksato-core`
- [ ] `zksato-broker` depends on `zksato-core`, `zksato-market`
- [ ] `zksato-strategy` depends on `zksato-core`, `zksato-market`, `zksato-risk`
- [ ] `zksato-portfolio` depends on `zksato-core`, `zksato-broker`
- [ ] `zksato-automation` depends on `zksato-core`, `zksato-risk`, `zksato-broker`, `zksato-portfolio`
- [ ] `zksato-api` depends on all domain packages
- [ ] `zksato-cli` depends on `zksato-core`, `zksato-api` (as client)

### Test Coverage
- [ ] All existing tests pass
- [ ] New package tests added
- [ ] Integration tests work cross-package
- [ ] Property-based tests for risk invariants
- [ ] Contract tests for protocols (BrokerAdapter, Strategy, Feed)

### Performance
- [ ] Import time < 500ms for each package
- [ ] Risk eval latency unchanged
- [ ] API startup time < 3s

### Documentation
- [ ] Each package has README.md
- [ ] API docs generated (pdoc or sphinx)
- [ ] Architecture diagram updated
- [ ] Migration guide published

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular dependencies | High | High | Strict layering; `zksato-core` at bottom; use protocols |
| Test breakage | High | Medium | Migrate tests with code; run CI after each package |
| Import performance | Medium | Low | Lazy imports; `__getattr__` for heavy submodules |
| Config complexity | Medium | Medium | Start simple; add environments gradually |
| Team adoption | Medium | High | Pair programming; clear docs; gradual rollout |

---

## 9. Success Criteria

- [ ] `uv sync` completes in < 30s
- [ ] `uv run pytest` passes all 487+ tests
- [ ] `uv run ruff check .` passes with 0 errors
- [ ] `uv run mypy .` passes with 0 errors
- [ ] Docker compose builds and starts in < 60s
- [ ] All entry points functional (`zksato`, `uvicorn zksato_api_app.main:app`)
- [ ] No regression in risk engine benchmarks
- [ ] Documentation updated and accurate

---

*This specification is the implementation contract for Phase 1. Update as decisions are made during implementation.*