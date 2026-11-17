# zksato Upgrade Plan: Leveraging gemini-cli Architecture Patterns

## Executive Summary

This plan outlines a phased approach to modernize zksato by adopting architectural patterns from gemini-cli, while preserving zksato's risk-first trading invariants. The upgrade focuses on modularity, observability, extensibility, and developer experience—without compromising the safety invariants defined in AGENTS.md.

---

## Current State Analysis

### zksato (Python/FastAPI)
- **Monolithic structure**: All code in `src/zksato/` with 40+ modules
- **Configuration**: Pydantic-settings with environment variables
- **Testing**: pytest with Hypothesis property tests (487 tests)
- **Observability**: Prometheus metrics, JSON logs, optional OpenTelemetry
- **Deployment**: Docker Compose with NGINX reverse proxy
- **Frontend**: Next.js 16 (port 3016) + Vite dashboard (port 5174)

### gemini-cli (TypeScript/Node.js)
- **Modular monorepo**: 7 packages (core, cli, sdk, a2a-server, devtools, vscode-ide-companion, test-utils)
- **Configuration**: TOML-based with schema validation (zod)
- **Testing**: vitest with extensive eval framework (50+ eval suites)
- **Observability**: Full OpenTelemetry (traces, metrics, logs), billing events
- **Agent Architecture**: Session-based, scheduler with tool execution, policy engine
- **Extensions**: Plugin system with custom commands, MCP servers
- **Sandboxing**: Docker/podman/Windows sandbox managers
- **A2A Protocol**: Agent-to-Agent communication standard

---

## Target Architecture: zksato v2.0

### High-Level Package Structure (Python Monorepo with Hatch/UV)

```
zksato/
├── packages/
│   ├── zksato-core/           # Core domain models, types, utilities
│   ├── zksato-risk/           # Risk engine, policies, rules
│   ├── zksato-market/         # Market data, feeds, adapters
│   ├── zksato-broker/         # Broker adapters (paper, settrade, ccxt)
│   ├── zksato-strategy/       # Strategy framework, indicators, backtesting
│   ├── zksato-portfolio/      # Portfolio, positions, P&L, reconciliation
│   ├── zksato-automation/     # Bot orchestration, scheduling, agent OS
│   ├── zksato-api/            # FastAPI routes, OpenAPI, auth
│   ├── zksato-cli/            # Typer-based CLI for operators
│   ├── zksato-dashboard/      # Vite/React dashboard (existing)
│   ├── zksato-frontend/       # Next.js operator UI (existing)
│   └── zksato-test-utils/     # Shared test fixtures, harnesses
├── apps/
│   ├── api/                   # FastAPI application entrypoint
│   ├── cli/                   # CLI entrypoint
│   └── worker/                # Background workers (reconciliation, alerts)
├── pyproject.toml             # Root workspace config (hatch/uv)
├── docker-compose.yml
└── README.md
```

---

## Phase 1: Foundation & Modularity (Weeks 1-3)

### 1.1 Convert to Monorepo with Hatch/UV Workspaces
**gemini-cli pattern**: npm workspaces with independent packages

**Actions**:
- [ ] Migrate to `uv` for faster dependency resolution
- [ ] Create `pyproject.toml` at root with `[tool.uv.workspace]`
- [ ] Split `src/zksato/` into domain packages under `packages/`
- [ ] Each package has own `pyproject.toml`, `src/`, `tests/`
- [ ] Shared `zksato-test-utils` package for fixtures/harnesses

**Deliverable**: `uv sync` installs all packages; `uv run pytest` works cross-package

### 1.2 Configuration System Overhaul
**gemini-cli pattern**: TOML config with zod schema validation, layered config (defaults → file → env → CLI)

**Actions**:
- [ ] Adopt TOML for complex config (trading rules, risk policies, broker adapters)
- [ ] Use `pydantic-settings` with `toml` config file support
- [ ] Define JSON schemas for all config sections (auto-generated from Pydantic)
- [ ] Config validation at startup with clear error messages
- [ ] Environment-specific config files (`.config.dev.toml`, `.config.uat.toml`)

**Files**:
```
config/
├── settings.toml              # Main config (versioned)
├── settings.local.toml        # Local overrides (gitignored)
├── schemas/
│   ├── risk-policy.schema.json
│   ├── broker-adapter.schema.json
│   └── strategy.schema.json
```

### 1.3 Core Domain Models Package (`zksato-core`)
**gemini-cli pattern**: `@google/gemini-cli-core` as foundation

**Contents**:
- `domain.py` → split into: `orders.py`, `fills.py`, `positions.py`, `accounts.py`, `events.py`
- `types.py` for shared enums, constants, type aliases
- `utils/` for serialization, datetime, money handling
- `exceptions.py` for domain-specific exceptions
- `ids.py` for idempotency keys, correlation IDs, ULIDs

**Key principle**: Zero dependencies on other zksato packages

---

## Phase 2: Risk Engine & Policy Framework (Weeks 3-5)

### 2.1 Policy Engine for Risk Rules
**gemini-cli pattern**: `policy-engine.ts` with sandbox policies, approval modes, topic policies

**Actions**:
- [ ] Create `zksato-risk` package with `PolicyEngine` class
- [ ] Risk rules as declarative policies (YAML/TOML), not hardcoded
- [ ] Policy evaluation with audit trail (decision + reason + context)
- [ ] Support for "approval modes" (paper, sandbox, uat, live) with escalating gates
- [ ] Four-eyes policy for live execution (dual authorization)

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

### 2.2 Risk Engine Refactor
- [ ] Extract `RiskEngine` into `zksato-risk` package
- [ ] Make risk checks composable (chain of responsibility)
- [ ] Add risk evaluation metrics (latency, decisions, overrides)
- [ ] Property-based tests for risk invariants (Hypothesis)

---

## Phase 3: Agent Orchestration & Automation (Weeks 5-8)

### 3.1 Scheduler & Tool Execution Framework
**gemini-cli pattern**: `scheduler/` with tool executor, hooks, parallel execution, state manager

**Actions**:
- [ ] Create `zksato-automation` package with `AgentScheduler`
- [ ] Tool registry pattern for trading operations (place_order, cancel, query_position)
- [ ] Hook system: pre-trade, post-trade, on-error, on-fill
- [ ] Parallel execution with configurable concurrency limits
- [ ] Checkpointing for long-running strategies (resume after restart)

**Core Types**:
```python
# zksato-automation/types.py
class Tool(ABC):
    name: str
    description: str
    parameters: Type[BaseModel]
    @abstractmethod
    async def execute(self, params: BaseModel, context: ToolContext) -> ToolResult

class ToolContext:
    session_id: str
    account_id: str
    correlation_id: str
    risk_context: RiskContext
    approval_token: Optional[ApprovalToken]
```

### 3.2 Agent OS Enhancement
**gemini-cli pattern**: Agent sessions with event streaming, tool display, content utils

**Actions**:
- [ ] Event-sourced agent sessions (append-only event log)
- [ ] Sub-account isolation with resource quotas
- [ ] Skill registry for trading capabilities (market-data, order-entry, risk-check)
- [ ] Streaming API for real-time agent updates (SSE/WebSocket)
- [ ] Agent-to-Agent (A2A) protocol for multi-agent workflows

### 3.3 Background Workers
**gemini-cli pattern**: Execution lifecycle service, shell execution service

**Actions**:
- [ ] Reconciliation worker (scheduled + event-driven)
- [ ] Alert/notification worker (outbox pattern, already exists)
- [ ] Market data ingestion worker
- [ ] Strategy evaluation worker (scheduled ticks)
- [ ] Health/checkpoint worker

---

## Phase 4: Broker & Market Adapters (Weeks 8-10)

### 4.1 Adapter Plugin System
**gemini-cli pattern**: Tool registry, MCP client/server for extensibility

**Actions**:
- [ ] Define `BrokerAdapter` protocol in `zksato-broker`
- [ ] Plugin entry points for dynamic discovery
- [ ] Built-in adapters: `PaperBroker`, `SettradeBroker`, `CCXTBroker`
- [ ] Adapter health checks, capability reporting
- [ ] Sandbox mode per adapter (isolated test environments)

### 4.2 Market Data Pipeline
**gemini-cli pattern**: File discovery service, git service (pipeline pattern)

**Actions**:
- [ ] Normalize market data into canonical `Bar`, `Quote`, `Trade` types
- [ ] Multi-source feed with fallback (primary → secondary → cached)
- [ ] Freshness/staleness monitoring with circuit breakers
- [ ] Replay capability for backtesting (deterministic)

---

## Phase 5: Observability & Developer Experience (Weeks 10-12)

### 5.1 Full OpenTelemetry Integration
**gemini-cli pattern**: Complete OTel setup (traces, metrics, logs, exporters)

**Actions**:
- [ ] Auto-instrumentation for FastAPI, SQLAlchemy, Redis, HTTPX
- [ ] Custom spans for: risk evaluation, order placement, fill processing, reconciliation
- [ ] Metrics: order latency, risk eval latency, fill rate, rejection rate, P&L
- [ ] Structured JSON logs with correlation IDs
- [ ] Dashboard in Grafana (or reuse existing Prometheus)

### 5.2 CLI for Operators (`zksato-cli`)
**gemini-cli pattern**: Rich CLI with ink (React for terminal), commands, autocomplete

**Actions**:
- [ ] Build with `typer` + `rich` for beautiful terminal UX
- [ ] Commands: `bot start|stop|status`, `order place|cancel|list`, `risk check|limits`, `reconcile`, `config validate|show`
- [ ] Tab completion, colored output, progress bars
- [ ] Non-interactive mode for scripting (`--output json`)
- [ ] Config validation command

### 5.3 Evaluation Framework
**gemini-cli pattern**: 50+ eval suites with vitest, LLM judges, statistical baselines

**Actions**:
- [ ] Create `evals/` directory with test suites
- [ ] Strategy backtest evaluation (Sharpe, drawdown, turnover vs benchmarks)
- [ ] Risk engine property tests (invariants under adversarial conditions)
- [ ] Reconciliation accuracy tests (synthetic broker scenarios)
- [ ] Latency/performance baselines with regression detection
- [ ] CI integration: fail on regression

---

## Phase 6: Frontend & API Modernization (Weeks 12-14)

### 6.1 API Versioning & Contracts
**gemini-cli pattern**: Stable-stringify, API conversion utils, version utils

**Actions**:
- [ ] API versioning in URL (`/v1/`, `/v2/`)
- [ ] OpenAPI spec as contract (generated from code)
- [ ] Contract testing (pact or schemathesis)
- [ ] Deprecation policy with headers

### 6.2 Dashboard Architecture
**gemini-cli pattern**: DevTools client, IDE companion (separate packages)

**Actions**:
- [ ] Split dashboard into: `zksato-dashboard-core` (React components), `zksato-dashboard-app` (Vite app)
- [ ] Shared component library with Storybook
- [ ] Real-time updates via SSE/WebSocket (not polling)
- [ ] TradingView chart integration as reusable component

---

## Phase 7: Security & Compliance Hardening (Weeks 14-16)

### 7.1 Secrets & Credential Management
**gemini-cli pattern**: Keychain service, API key credential storage, OAuth

**Actions**:
- [ ] Integrate with OS keychain (keyring) for local dev
- [ ] Support for HashiCorp Vault / AWS Secrets Manager in prod
- [ ] Credential rotation without restart
- [ ] Audit log for all credential access

### 7.2 Sandboxed Execution
**gemini-cli pattern**: SandboxManager (Docker, podman, Windows)

**Actions**:
- [ ] Paper trading in isolated containers (network, filesystem)
- [ ] Strategy execution sandbox (no network, limited CPU/memory)
- [ ] UAT broker sandbox with traffic mirroring
- [ ] SELinux/AppArmor profiles for containers

---

## Migration Strategy

### Branch Strategy
```
main (v1.x) ──────────────────────────────────────────────►
  │
  └── upgrade/v2-foundation (Phase 1)
        │
        └── upgrade/v2-risk (Phase 2)
              │
              └── upgrade/v2-automation (Phase 3)
                    │
                    └── upgrade/v2-brokers (Phase 4)
                          │
                          └── upgrade/v2-observability (Phase 5)
                                │
                                └── upgrade/v2-frontend (Phase 6)
                                      │
                                      └── upgrade/v2-security (Phase 7)
                                            │
                                            └── main (v2.0) ◄── merge with squash
```

### Validation Gates (Per Phase)
Each phase must pass before merging:
```bash
# Standard validation
uv run ruff check .
uv run mypy .
uv run pytest -m "not uat and not performance"

# Phase-specific
uv run pytest packages/zksato-risk/tests/ -v
uv run pytest evals/ -v              # Phase 5+
uv run zksato config validate        # Phase 1+
```

### Rollback Plan
- Each phase deployed behind feature flags
- Database migrations are backward-compatible (expand-only)
- Canary deployment to dev → uat → prod
- 30-minute rollback window with automated revert

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing API contracts | OpenAPI contract tests; versioned APIs; deprecation window |
| Data migration complexity | Expand-only migrations; dual-write during transition; reconciliation verification |
| Performance regression | Performance baselines in evals; CI gate; load testing in staging |
| Team learning curve | Pair programming; architecture decision records (ADRs); documentation |
| Feature freeze during upgrade | Phase gates allow incremental value delivery; v1.x maintained on main |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Test suite time | < 60s (currently ~15s, but growing) |
| Risk eval latency (p99) | < 5ms |
| Order placement latency (p99) | < 50ms |
| Reconciliation accuracy | 100% (zero drift) |
| Config validation errors | 0 in CI |
| Eval suite pass rate | 100% |
| Security scan findings | 0 critical, 0 high |

---

## Appendix: Key gemini-cli Patterns Adapted

| gemini-cli Pattern | zksato Adaptation |
|--------------------|-------------------|
| Monorepo workspaces | UV/Hatch workspaces |
| Policy engine (TOML + zod) | Risk policies (TOML + pydantic) |
| Scheduler + tool executor | AgentScheduler + TradingTool registry |
| Agent sessions + events | Event-sourced agent OS sessions |
| MCP client/server | Broker/Strategy adapter protocol |
| Eval framework (vitest + LLM judge) | Hypothesis + custom evals |
| OpenTelemetry (full stack) | OTel auto-instrument + custom spans |
| SandboxManager | Paper/UAT sandbox containers |
| Keychain service | OS keyring + Vault integration |
| Extension loader | Strategy/Indicator plugin system |
| Checkpointing | Strategy/Session resume after restart |
| A2A protocol | Inter-agent trading workflows |

---

## Next Steps

1. **Approve this plan** → Create GitHub issue with phase breakdown
2. **Set up UV monorepo** → Phase 1.1 (1 week)
3. **Extract core domain** → Phase 1.3 (1 week)
4. **Begin risk policy engine** → Phase 2 (2 weeks)
5. **Weekly sync** on progress, blockers, scope adjustments

---

*This plan is a living document. Update with ADRs as decisions are made.*