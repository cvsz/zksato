# gemini-cli Patterns for zksato Upgrade

## Pattern Mapping Table

| # | gemini-cli Pattern | Package/Module | zksato Application | Priority |
|---|-------------------|----------------|-------------------|----------|
| 1 | **Monorepo Workspaces** | Root `package.json` with `workspaces` | UV/Hatch workspaces in `pyproject.toml` | P0 |
| 2 | **Core Package** | `@google/gemini-cli-core` | `zksato-core` - domain types, utilities, config | P0 |
| 3 | **Policy Engine** | `packages/core/src/policy/policy-engine.ts` | `zksato-risk` policy engine for trading rules | P1 |
| 4 | **Scheduler + Tool Executor** | `packages/core/src/scheduler/` | `zksato-automation` AgentScheduler + TradingTool registry | P1 |
| 5 | **Agent Sessions (Event-Sourced)** | `packages/core/src/agent/agent-session.ts` | `zksato-automation` AgentOS session with event log | P1 |
| 6 | **MCP Client/Server** | `packages/core/src/tools/mcp-client.ts` | Broker/Strategy adapter protocol (plugin system) | P2 |
| 7 | **Extension Loader** | `packages/core/src/utils/extensionLoader.ts` | Strategy/Indicator/Broker plugin discovery | P2 |
| 8 | **Eval Framework** | `evals/` with vitest + LLM judges | Hypothesis property tests + custom eval suites | P2 |
| 9 | **OpenTelemetry (Full Stack)** | `packages/core/src/` OTel setup | Auto-instrumentation + custom spans for trading | P1 |
| 10 | **SandboxManager** | `packages/core/src/services/sandboxManager.ts` | Paper/UAT sandbox containers | P2 |
| 11 | **Keychain Service** | `packages/core/src/services/keychainService.ts` | OS keyring + Vault/AWS Secrets Manager | P1 |
| 12 | **Checkpointing** | `packages/core/src/utils/checkpointUtils.ts` | Strategy/Session resume after restart | P2 |
| 13 | **A2A Protocol** | `packages/a2a-server/` | Inter-agent trading workflows | P3 |
| 14 | **Rich CLI (ink)** | `packages/cli/` with React/ink | `zksato-cli` with Typer + Rich | P2 |
| 15 | **Configuration (TOML + zod)** | `packages/core/src/config/` | TOML config + pydantic validation | P0 |
| 16 | **Shell Execution Service** | `packages/core/src/services/shellExecutionService.ts` | Secure command execution for ops | P3 |
| 17 | **Memory/Context Manager** | `packages/core/src/context/memoryContextManager.ts` | Strategy context, research memory | P3 |
| 18 | **Skill Manager** | `packages/core/src/skills/skillManager.ts` | Trading skill registry (market data, orders, risk) | P1 |
| 19 | **Tool Registry** | `packages/core/src/tools/tool-registry.ts` | Trading tool registry with capabilities | P1 |
| 20 | **Hook System** | `packages/core/src/hooks/` | Pre/post trade hooks, error handling | P1 |
| 21 | **Stable Stringify** | `packages/core/src/policy/stable-stringify.ts` | Deterministic serialization for idempotency | P1 |
| 22 | **Error Classification** | `packages/core/src/availability/errorClassification.ts` | Broker error classification, retry policies | P2 |
| 23 | **Model Router/Fallback** | `packages/core/src/routing/` | Multi-broker failover, feed fallback | P2 |
| 24 | **Confirmation Bus** | `packages/core/src/confirmation-bus/` | Four-eyes approval for live orders | P1 |
| 25 | **Telemetry/Billing Events** | `packages/core/src/telemetry/` | Trading metrics, audit events | P1 |

---

## Detailed Pattern Analysis

### 1. Monorepo Workspaces (P0)
**gemini-cli**: npm workspaces with 7 packages, independent versioning, shared tooling

**zksato Implementation**:
```toml
# Root pyproject.toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]

[tool.uv.sources]
zksato-core = { workspace = true }
zksato-risk = { workspace = true }
# ...
```

**Benefits**:
- Independent development/testing of domain packages
- Clear ownership boundaries (matches AGENTS.md ownership map)
- Faster CI (only test changed packages)
- Easier to extract packages as separate libraries later

### 2. Core Package (P0)
**gemini-cli**: `@google/gemini-cli-core` exports 300+ modules, foundation for all packages

**zksato Implementation**: `zksato-core` with:
- `types.py` - Shared enums (OrderSide, OrderType, TradingMode, etc.)
- `ids.py` - ULID generation, idempotency keys, correlation IDs
- `money.py` - Decimal-based money handling (THB, USD), currency conversion
- `datetime.py` - Bangkok timezone, market session helpers
- `serialization.py` - JSON/msgpack, stable stringify for idempotency
- `exceptions.py` - Domain exception hierarchy
- `events.py` - Event base classes, event store interface
- `config.py` - BaseConfig with TOML + env loading

**Key Principle**: Zero dependencies on other zksato packages

### 3. Policy Engine (P1)
**gemini-cli**: `PolicyEngine` with sandbox policies, approval modes, topic policies, integrity checks

**zksato Application**: Risk policies as declarative configuration
```toml
# config/policies/risk/trading.toml
[policy.daily_loss_limit]
type = "notional"
limit = 50000
currency = "THB"
action = "reject"
approval_mode = ["live", "uat"]

[policy.position_concentration]
type = "concentration"
max_single_symbol_pct = 0.15
max_sector_pct = 0.30
action = "warn"
approval_mode = ["live"]

[policy.feed_freshness]
type = "staleness"
max_age_ms = 5000
action = "fail_closed"
approval_mode = ["paper", "sandbox", "uat", "live"]
```

**Architecture**:
```python
# zksato-risk/src/zksato_risk/policies/
class Policy(ABC):
    type: str
    @abstractmethod
    def evaluate(self, context: RiskContext) -> PolicyDecision

class PolicyEngine:
    def __init__(self, registry: PolicyRegistry):
        self.registry = registry
    
    async def evaluate(self, context: RiskContext) -> RiskResult:
        decisions = []
        for policy in self.registry.get_active(context.approval_mode):
            decisions.append(await policy.evaluate(context))
        return RiskResult(decisions=decisions)
```

### 4. Scheduler + Tool Executor (P1)
**gemini-cli**: `Scheduler` with `ToolExecutor`, hooks, parallel execution, state manager

**zksato Application**: Trading automation with tool registry
```python
# zksato-automation/src/zksato_automation/tools/registry.py
class TradingTool(Protocol):
    name: str
    description: str
    parameters: Type[BaseModel]
    required_approval: ApprovalLevel
    
    async def execute(self, params: BaseModel, ctx: ToolContext) -> ToolResult

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, TradingTool] = {}
    
    def register(self, tool: TradingTool) -> None:
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> TradingTool:
        return self._tools[name]

# Built-in tools:
# - get_quote(symbol) -> Quote
# - place_order(order: OrderRequest) -> OrderResult
# - cancel_order(order_id: str) -> CancelResult
# - get_position(symbol) -> Position
# - check_risk(order: OrderRequest) -> RiskResult
# - reconcile(account_id: str) -> ReconciliationResult
```

**Hook System** (from gemini-cli `scheduler/hooks.ts`):
```python
class HookManager:
    def __init__(self):
        self.pre_tool: list[Callable] = []
        self.post_tool: list[Callable] = []
        self.on_error: list[Callable] = []
    
    async def run_pre(self, tool: TradingTool, params: BaseModel, ctx: ToolContext):
        for hook in self.pre_tool:
            await hook(tool, params, ctx)
```

### 5. Agent Sessions (Event-Sourced) (P1)
**gemini-cli**: `AgentSession` with event streaming, tool display, content utils, trajectory

**zksato Application**: Event-sourced agent OS sessions
```python
# zksato-automation/src/zksato_automation/agent_os/session.py
@dataclass
class AgentEvent:
    event_id: ULID
    session_id: ULID
    timestamp: datetime
    event_type: AgentEventType
    payload: dict
    correlation_id: ULID | None = None

class AgentSession:
    def __init__(self, session_id: ULID, subaccount_id: str):
        self.session_id = session_id
        self.subaccount_id = subaccount_id
        self.events: list[AgentEvent] = []
        self.state: SessionState = SessionState.CREATED
    
    def append_event(self, event: AgentEvent) -> None:
        self.events.append(event)
        self._apply_event(event)
    
    async def execute_tool(self, tool_name: str, params: BaseModel) -> ToolResult:
        # Pre-hook
        # Risk check (non-bypassable)
        # Execute
        # Post-hook
        # Append event
```

**Sub-account Isolation** (from gemini-cli `FolderTrustDiscoveryService`):
```python
class SubAccount:
    def __init__(self, account_id: str, parent_id: str, quotas: Quotas):
        self.account_id = account_id
        self.parent_id = parent_id
        self.quotas = quotas  # max_orders, max_notional, max_positions
        self.session: AgentSession | None = None
    
    def can_execute(self, order: OrderRequest) -> bool:
        # Check quotas, risk limits, WITHDRAW invariant
```

### 6. MCP Client/Server → Adapter Protocol (P2)
**gemini-cli**: MCP client for tool discovery, MCP server for exposing tools

**zksato Application**: Broker/Strategy adapter protocol
```python
# zksato-broker/src/zksato_broker/protocol.py
class BrokerAdapter(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def capabilities(self) -> set[Capability]: ...

    async def connect(self, config: BrokerConfig) -> None: ...
    async def disconnect(self) -> None: ...

    async def place_order(self, order: OrderRequest) -> OrderResult: ...
    async def cancel_order(self, order_id: str) -> CancelResult: ...
    async def get_positions(self) -> list[Position]: ...
    async def get_account(self) -> Account: ...
    async def health_check(self) -> HealthStatus: ...


# Plugin discovery via entry points
# pyproject.toml:
# [project.entry-points."zksato.brokers"]
# paper = "zksato_broker.paper:PaperBroker"
# settrade = "zksato_broker.settrade:SettradeBroker"
# ccxt = "zksato_broker.ccxt:CCXTBroker"
```

### 7. Extension Loader → Plugin System (P2)
**gemini-cli**: `extensionLoader.ts` loads custom commands, MCP servers, skills

**zksato Application**: Strategy/Indicator/Broker plugins
```python
# zksato-strategy/src/zksato_strategy/registry.py
class StrategyPlugin(Protocol):
    name: str
    version: str
    description: str
    parameter_space: ParameterSpace

    def create_strategy(self, config: StrategyConfig) -> Strategy: ...


class PluginRegistry:
    def __init__(self):
        self.strategies: dict[str, StrategyPlugin] = {}
        self.indicators: dict[str, IndicatorPlugin] = {}
        self.brokers: dict[str, BrokerAdapter] = {}

    def discover(self) -> None:
        # Load from entry points
        for ep in importlib.metadata.entry_points(group="zksato.strategies"):
            self.strategies[ep.name] = ep.load()
```

### 8. Eval Framework (P2)
**gemini-cli**: 50+ eval suites with vitest, LLM judges, statistical baselines, regression detection

**zksato Application**: Comprehensive evaluation suites
```
evals/
├── risk/
│   ├── test_invariants.py          # Property-based risk invariants
│   ├── test_latency.py             # Risk eval latency benchmarks
│   └── test_adversarial.py         # Adversarial order scenarios
├── reconciliation/
│   ├── test_accuracy.py            # Reconciliation accuracy vs synthetic brokers
│   ├── test_edge_cases.py          # Partial fills, cancels, rejects
│   └── test_restart_recovery.py    # Restart-safe reconciliation
├── strategy/
│   ├── test_backtest_fidelity.py   # Backtest vs live simulation
│   ├── test_parameter_stability.py # Optuna parameter stability
│   └── test_walkforward.py         # Walk-forward validation
├── performance/
│   ├── test_api_latency.py         # API endpoint latency
│   ├── test_throughput.py          # Orders/sec, risk evals/sec
│   └── test_memory.py              # Memory usage under load
└── security/
    ├── test_auth.py                # Auth bypass attempts
    ├── test_secrets.py             # Secret leakage detection
    └── test_rbac.py                # Role-based access control
```

**CI Integration**:
```yaml
# .github/workflows/evals.yml
- name: Run evals
  run: |
    uv run pytest evals/ -v --benchmark-only
    uv run pytest evals/risk/ -v
    uv run pytest evals/reconciliation/ -v
```

### 9. OpenTelemetry Full Stack (P1)
**gemini-cli**: Complete OTel setup with traces, metrics, logs, multiple exporters

**zksato Application**: Trading-focused observability
```python
# zksato-core/src/zksato_core/observability.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrument.fastapi import FastAPIInstrumentor
from opentelemetry.instrument.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrument.redis import RedisInstrumentor
from opentelemetry.instrument.httpx import HTTPXClientInstrumentor


def setup_observability(config: ObservabilityConfig) -> None:
    # Traces
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=config.otlp_endpoint))
    )

    # Metrics
    metrics.set_meter_provider(MeterProvider())
    metrics.get_meter_provider().add_metric_reader(
        PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=config.otlp_endpoint))
    )

    # Auto-instrumentation
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()


# Custom spans for trading
tracer = trace.get_tracer("zksato.trading")


@contextmanager
def risk_evaluation_span(order: OrderRequest):
    with tracer.start_as_current_span("risk.evaluate") as span:
        span.set_attribute("order.symbol", order.symbol)
        span.set_attribute("order.side", order.side.value)
        span.set_attribute("order.notional", str(order.notional))
        yield span


@contextmanager
def order_placement_span(order: OrderRequest, broker: str):
    with tracer.start_as_current_span("order.place") as span:
        span.set_attribute("broker", broker)
        yield span
```

**Key Metrics**:
- `zksato.risk.evaluation.duration` (histogram)
- `zksato.risk.decision` (counter: allow/reject/warn/override)
- `zksato.order.latency` (histogram)
- `zksato.order.fills` (counter)
- `zksato.reconciliation.drift` (gauge)
- `zksato.portfolio.pnl` (gauge)
- `zksato.broker.health` (gauge)

### 10. SandboxManager (P2)
**gemini-cli**: `SandboxManager` with Docker, podman, Windows support

**zksato Application**: Isolated paper/UAT environments
```python
# zksato-broker/src/zksato_broker/sandbox.py
class SandboxManager:
    def __init__(self, runtime: SandboxRuntime = SandboxRuntime.DOCKER):
        self.runtime = runtime
    
    async def create_paper_sandbox(self, config: PaperSandboxConfig) -> Sandbox:
        """Create isolated paper trading environment."""
        # Network isolation (no external access)
        # Filesystem isolation (own data volume)
        # Resource limits (CPU, memory)
        # Own PostgreSQL/Redis instances
    
    async def create_uat_sandbox(self, broker: str) -> Sandbox:
        """Create UAT sandbox with traffic mirroring."""
        # Mirror production traffic to sandbox
        # Isolated broker credentials
        # Separate database
```

### 11. Keychain Service (P1)
**gemini-cli**: `KeychainService` with OS keychain, encrypted storage

**zksato Application**: Secure credential management
```python
# zksato-core/src/zksato_core/secrets.py
class SecretManager:
    def __init__(self, backend: SecretBackend = SecretBackend.AUTO):
        self.backend = backend
    
    async def get_secret(self, key: str) -> str:
        # Try: OS keyring → Vault → AWS Secrets Manager → env var
    
    async def set_secret(self, key: str, value: str) -> None:
        # Store in configured backend
    
    async def rotate_secret(self, key: str, new_value: str) -> None:
        # Rotate without restart (notify consumers)

# Usage in broker adapters
class SettradeBroker:
    def __init__(self, secret_manager: SecretManager):
        self.secrets = secret_manager
    
    async def connect(self):
        app_id = await self.secrets.get_secret("settrade.app_id")
        app_secret = await self.secrets.get_secret("settrade.app_secret")
        # ...
```

### 12. Checkpointing (P2)
**gemini-cli**: `checkpointUtils.ts` for conversation/session checkpointing

**zksato Application**: Strategy/Session resume
```python
# zksato-automation/src/zksato_automation/scheduler/state.py
@dataclass
class SessionCheckpoint:
    session_id: ULID
    timestamp: datetime
    state: SessionState
    pending_orders: list[OrderRequest]
    strategy_state: dict  # Strategy-specific state
    risk_context: RiskContext
    event_log_position: int  # For event-sourced resume


class CheckpointManager:
    async def save_checkpoint(self, session: AgentSession) -> None:
        checkpoint = SessionCheckpoint.from_session(session)
        await self.store.save(checkpoint)

    async def restore_session(self, session_id: ULID) -> AgentSession:
        checkpoint = await self.store.load(session_id)
        session = AgentSession(session_id, checkpoint.subaccount_id)
        # Replay events from checkpoint.event_log_position
        # Restore strategy state
        # Re-submit pending orders (idempotent)
        return session
```

### 13. A2A Protocol (P3)
**gemini-cli**: `packages/a2a-server/` implements Agent-to-Agent protocol

**zksato Application**: Multi-agent trading workflows
```python
# zksato-automation/src/zksato_automation/agent_os/a2a.py
class A2AMessage:
    message_id: ULID
    from_agent: str
    to_agent: str
    payload: dict
    message_type: A2AMessageType  # REQUEST, RESPONSE, EVENT, HEARTBEAT

class AgentRegistry:
    def __init__(self):
        self.agents: dict[str, AgentInfo] = {}
    
    async def send_message(self, msg: A2AMessage) -> A2AMessage:
        # Route to target agent
        # Handle timeouts, retries
        # Correlation for request/response

# Use cases:
# - Risk agent → Execution agent: "Pre-check this order"
# - Scanner agent → Strategy agent: "New signal for SYMBOL"
# - Reconciliation agent → Portfolio agent: "Position drift detected"
```

### 14. Rich CLI (P2)
**gemini-cli**: `ink` (React for terminal) with spinners, gradients, interactive prompts

**zksato Application**: `Typer` + `Rich` for operator CLI
```python
# zksato-cli/src/zksato_cli/commands/bot.py
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()
console = Console()


@app.command()
def start(
    strategy: str = typer.Option(..., "--strategy", "-s", help="Strategy name"),
    symbol: str = typer.Option(..., "--symbol", help="Trading symbol"),
    capital: float = typer.Option(..., "--capital", help="Allocated capital"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Paper mode"),
):
    """Start a trading bot."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting bot...", total=None)
        # Start bot via API
        result = await api_client.bot_start(strategy, symbol, capital, dry_run)
        progress.update(task, completed=True)

    console.print(f"[green]Bot started:[/green] {result.bot_id}")


@app.command()
def status(
    bot_id: str = typer.Argument(..., help="Bot ID"),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Show bot status."""
    result = await api_client.bot_status(bot_id)
    if json_output:
        console.print_json(result.model_dump_json())
    else:
        table = Table(title=f"Bot {bot_id} Status")
        table.add_column("Field")
        table.add_column("Value")
        for k, v in result.model_dump().items():
            table.add_row(k, str(v))
        console.print(table)
```

### 15. Configuration (TOML + zod) (P0)
**gemini-cli**: TOML config with zod schema validation, layered (defaults → file → env → CLI)

**zksato Application**: Pydantic + TOML with JSON schema generation
```python
# zksato-core/src/zksato_core/config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import tomllib
from pathlib import Path


class RiskPolicyConfig(BaseModel):
    daily_loss_limit: NotionalLimit = Field(default_factory=NotionalLimit)
    position_concentration: ConcentrationLimit = Field(default_factory=ConcentrationLimit)
    feed_freshness: StalenessLimit = Field(default_factory=StalenessLimit)


class BrokerConfig(BaseModel):
    paper: PaperBrokerConfig = Field(default_factory=PaperBrokerConfig)
    settrade: SettradeConfig | None = None
    ccxt: CCXTConfig | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZKSATO_",
        env_nested_delimiter="__",
        toml_file=Path("config/settings.toml"),
        extra="ignore",
    )

    trading_mode: TradingMode = TradingMode.PAPER
    database_url: str
    redis_url: str
    risk: RiskPolicyConfig = Field(default_factory=RiskPolicyConfig)
    brokers: BrokerConfig = Field(default_factory=BrokerConfig)

    @classmethod
    def load(cls, env: str | None = None) -> "Settings":
        """Load with environment-specific overrides."""
        data = {}
        for f in (
            [Path("config/settings.toml")]
            + ([Path(f"config/environments/{env}.toml")] if env else [])
            + [Path("config/settings.local.toml")]
        ):
            if f.exists():
                with f.open("rb") as fp:
                    deep_merge(data, tomllib.load(fp))
        return cls(**data)


# Generate JSON schemas for validation
def generate_schemas():
    for name, model in [("risk-policy", RiskPolicyConfig), ("broker", BrokerConfig)]:
        schema = model.model_json_schema()
        Path(f"config/schemas/{name}.schema.json").write_text(json.dumps(schema, indent=2))
```

### 16. Shell Execution Service (P3)
**gemini-cli**: Secure shell execution with sandboxing, timeouts, output capture

**zksato Application**: Operational command execution
```python
# zksato-automation/src/zksato_automation/workers/shell.py
class ShellExecutor:
    async def run(
        self,
        command: list[str],
        timeout: float = 30.0,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        capture_output: bool = True,
    ) -> ShellResult:
        # Run in sandbox if configured
        # Timeout enforcement
        # Output capture with size limits
        # Audit logging
```

### 17. Memory/Context Manager (P3)
**gemini-cli**: `memoryContextManager.ts` for conversation memory, context graphs

**zksato Application**: Strategy research memory, context persistence
```python
# zksato-strategy/src/zksato_strategy/research/memory.py
class StrategyMemory:
    def __init__(self, store: MemoryStore):
        self.store = store
    
    async def save_context(self, strategy_id: str, context: StrategyContext) -> None:
        # Save: parameters, regime, performance, notes
    
    async def load_context(self, strategy_id: str) -> StrategyContext | None:
        # Load for warm start, regime detection
    
    async def save_research_note(self, note: ResearchNote) -> None:
        # Link to strategy, symbol, timeframe
```

### 18. Skill Manager (P1)
**gemini-cli**: `skillManager.ts` loads skills, manages lifecycle, provides tools

**zksato Application**: Trading skill hub (matches AGENTS.md Agent OS)
```python
# zksato-automation/src/zksato_automation/agent_os/skills.py
class TradingSkill(Protocol):
    name: str
    description: str
    required_capabilities: set[Capability]
    
    async def execute(self, params: BaseModel, ctx: SkillContext) -> SkillResult:

class SkillRegistry:
    def __init__(self):
        self.skills: dict[str, TradingSkill] = {}
    
    def register(self, skill: TradingSkill) -> None:
        self.skills[skill.name] = skill

# Built-in skills (from AGENTS.md):
# - real_time_quotes(symbols) -> list[Quote]
# - technical_indicators(symbol, indicators) -> dict[str, float]
# - account_telemetry() -> AccountSnapshot
# - cancel_order(order_id) -> CancelResult
# - submit_order(order) -> OrderResult (with risk check)
# - get_positions() -> list[Position]
# - get_risk_limits() -> RiskLimits
```

### 19. Tool Registry (P1)
**gemini-cli**: `tool-registry.ts` with tool definitions, names, schemas

**zksato Application**: Unified tool registry for CLI, API, Agent OS
```python
# zksato-automation/src/zksato_automation/tools/registry.py
from pydantic import BaseModel, create_model


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, TradingTool] = {}
        self.schemas: dict[str, Type[BaseModel]] = {}

    def register(self, tool: TradingTool) -> None:
        self.tools[tool.name] = tool
        self.schemas[tool.name] = tool.parameters

    def get_schema(self, name: str) -> dict:
        """Return JSON schema for tool (for LLM function calling)."""
        return self.schemas[name].model_json_schema()

    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        tool = self.tools[name]
        validated = tool.parameters(**params)
        return await tool.execute(validated, ctx)


# Auto-generate OpenAPI from tool registry
def generate_tool_openapi(registry: ToolRegistry) -> dict:
    paths = {}
    for name, tool in registry.tools.items():
        paths[f"/tools/{name}"] = {
            "post": {
                "summary": tool.description,
                "requestBody": {
                    "content": {"application/json": {"schema": registry.get_schema(name)}}
                },
                "responses": {"200": {"description": "Tool result"}},
            }
        }
    return {"paths": paths}
```

### 20. Hook System (P1)
**gemini-cli**: `hooks/index.ts` with hook types, registration, execution

**zksato Application**: Trading lifecycle hooks
```python
# zksato-automation/src/zksato_automation/scheduler/hooks.py
class HookType(Enum):
    PRE_RISK_CHECK = "pre_risk_check"
    POST_RISK_CHECK = "post_risk_check"
    PRE_ORDER_PLACE = "pre_order_place"
    POST_ORDER_PLACE = "post_order_place"
    ON_FILL = "on_fill"
    ON_REJECT = "on_reject"
    ON_RECONCILIATION_DRIFT = "on_reconciliation_drift"
    ON_RISK_LIMIT_BREACH = "on_risk_limit_breach"


class HookManager:
    def __init__(self):
        self.hooks: dict[HookType, list[Callable]] = defaultdict(list)

    def register(self, hook_type: HookType, fn: Callable) -> None:
        self.hooks[hook_type].append(fn)

    async def run(self, hook_type: HookType, *args, **kwargs) -> list[Any]:
        results = []
        for hook in self.hooks[hook_type]:
            try:
                result = await hook(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_type} failed: {e}")
        return results


# Example usage in scheduler:
async def execute_tool(self, tool: TradingTool, params: BaseModel, ctx: ToolContext):
    await self.hooks.run(HookType.PRE_RISK_CHECK, tool, params, ctx)
    risk_result = await self.risk_engine.evaluate(ctx)
    await self.hooks.run(HookType.POST_RISK_CHECK, tool, params, ctx, risk_result)

    if not risk_result.allowed:
        await self.hooks.run(HookType.ON_REJECT, tool, params, ctx, risk_result)
        raise RiskRejected(risk_result)

    await self.hooks.run(HookType.PRE_ORDER_PLACE, tool, params, ctx)
    result = await tool.execute(params, ctx)
    await self.hooks.run(HookType.POST_ORDER_PLACE, tool, params, ctx, result)
    return result
```

### 21. Stable Stringify (P1)
**gemini-cli**: `stable-stringify.ts` for deterministic serialization (critical for caching, idempotency)

**zksato Application**: Idempotency keys, order deduplication
```python
# zksato-core/src/zksato_core/serialization.py
import json
from typing import Any


def stable_json_dumps(obj: Any) -> str:
    """Deterministic JSON serialization for idempotency keys."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_idempotency_key(order: OrderRequest) -> str:
    """Generate deterministic idempotency key from order."""
    key_data = {
        "symbol": order.symbol,
        "side": order.side.value,
        "type": order.type.value,
        "quantity": str(order.quantity),
        "price": str(order.price) if order.price else None,
        "account_id": order.account_id,
        "strategy_id": order.strategy_id,
        "timestamp": order.timestamp.isoformat() if order.timestamp else None,
    }
    # Hash for fixed-length key
    import hashlib

    return hashlib.sha256(stable_json_dumps(key_data).encode()).hexdigest()[:32]


# Usage in broker adapters:
async def place_order(self, order: OrderRequest) -> OrderResult:
    idempotency_key = generate_idempotency_key(order)
    # Check if already processed
    existing = await self.store.get_order_by_idempotency(idempotency_key)
    if existing:
        return existing
    # ... place order
```

### 22. Error Classification (P2)
**gemini-cli**: `errorClassification.ts` classifies errors for retry, fallback, user-facing

**zksato Application**: Broker error handling, retry policies
```python
# zksato-broker/src/zksato_broker/errors.py
class BrokerErrorCategory(Enum):
    TRANSIENT = "transient"  # Retry with backoff
    RATE_LIMITED = "rate_limited"  # Retry after delay
    AUTH_FAILED = "auth_failed"  # Re-authenticate
    INVALID_ORDER = "invalid_order"  # Don't retry, fix order
    REJECTED = "rejected"  # Order rejected by exchange
    UNKNOWN = "unknown"  # Alert, manual intervention


class BrokerError(Exception):
    def __init__(
        self,
        message: str,
        category: BrokerErrorCategory,
        original_error: Exception | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.category = category
        self.original_error = original_error
        self.retry_after = retry_after


def classify_error(error: Exception, broker: str) -> BrokerError:
    """Classify broker errors for consistent handling."""
    error_str = str(error).lower()

    if "timeout" in error_str or "connection" in error_str:
        return BrokerError(str(error), BrokerErrorCategory.TRANSIENT, error)
    elif "rate limit" in error_str or "429" in error_str:
        return BrokerError(str(error), BrokerErrorCategory.RATE_LIMITED, error)
    elif "unauthorized" in error_str or "401" in error_str:
        return BrokerError(str(error), BrokerErrorCategory.AUTH_FAILED, error)
    elif "invalid" in error_str or "bad request" in error_str:
        return BrokerError(str(error), BrokerErrorCategory.INVALID_ORDER, error)
    elif "rejected" in error_str:
        return BrokerError(str(error), BrokerErrorCategory.REJECTED, error)
    else:
        return BrokerError(str(error), BrokerErrorCategory.UNKNOWN, error)


# Retry policy per category
RETRY_POLICIES = {
    BrokerErrorCategory.TRANSIENT: RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0),
    BrokerErrorCategory.RATE_LIMITED: RetryPolicy(max_attempts=5, base_delay=5.0, max_delay=60.0),
    BrokerErrorCategory.AUTH_FAILED: RetryPolicy(
        max_attempts=1, base_delay=0, max_delay=0
    ),  # Re-auth then retry
    BrokerErrorCategory.INVALID_ORDER: RetryPolicy(max_attempts=0),
    BrokerErrorCategory.REJECTED: RetryPolicy(max_attempts=0),
    BrokerErrorCategory.UNKNOWN: RetryPolicy(max_attempts=1, base_delay=10.0, max_delay=10.0),
}
```

### 23. Model Router/Fallback (P2)
**gemini-cli**: `modelRouterService.ts` with routing strategies, fallback chains

**zksato Application**: Multi-broker failover, feed fallback
```python
# zksato-market/src/zksato_market/feeds/composite.py
class FeedRouter:
    def __init__(
        self, feeds: list[MarketFeed], strategy: RoutingStrategy = RoutingStrategy.PRIORITY
    ):
        self.feeds = feeds
        self.strategy = strategy
        self.active_feed: MarketFeed | None = None

    async def connect(self) -> None:
        for feed in self.feeds:
            try:
                await feed.connect()
                self.active_feed = feed
                logger.info(f"Connected to primary feed: {feed.name}")
                return
            except Exception as e:
                logger.warning(f"Feed {feed.name} failed: {e}")
        raise ConnectionError("All feeds failed")

    async def on_feed_failure(self, feed: MarketFeed) -> None:
        if feed != self.active_feed:
            return
        logger.warning(f"Primary feed {feed.name} failed, failing over")
        for fallback in self.feeds:
            if fallback != feed:
                try:
                    await fallback.connect()
                    self.active_feed = fallback
                    logger.info(f"Failed over to: {fallback.name}")
                    return
                except Exception as e:
                    logger.warning(f"Fallback {fallback.name} failed: {e}")
        # All failed - fail closed
        await self.hooks.run(HookType.ON_FEED_FAILURE)
        raise FeedUnavailable("All market feeds unavailable")


# Broker failover
class BrokerRouter:
    def __init__(self, brokers: list[BrokerAdapter]):
        self.brokers = {b.name: b for b in brokers}
        self.primary: str | None = None

    async def place_order(self, order: OrderRequest) -> OrderResult:
        # Try primary
        if self.primary and self.primary in self.brokers:
            try:
                return await self.brokers[self.primary].place_order(order)
            except BrokerError as e:
                if e.category in (BrokerErrorCategory.TRANSIENT, BrokerErrorCategory.RATE_LIMITED):
                    # Try failover
                    pass
        # Try other brokers with same capability
        for broker in self.brokers.values():
            if broker.name != self.primary and order.required_capability in broker.capabilities:
                try:
                    return await broker.place_order(order)
                except BrokerError:
                    continue
        raise BrokerUnavailable("No available broker for order")
```

### 24. Confirmation Bus (P1)
**gemini-cli**: `confirmation-bus/message-bus.ts` for approval workflows

**zksato Application**: Four-eyes approval for live orders
```python
# zksato-risk/src/zksato_risk/policies/approval.py
class ApprovalToken:
    token_id: ULID
    order_id: ULID
    requested_by: str
    approved_by: list[str] = field(default_factory=list)
    required_approvers: int = 2  # Four-eyes
    status: ApprovalStatus = ApprovalStatus.PENDING
    expires_at: datetime
    metadata: dict = field(default_factory=dict)


class ConfirmationBus:
    def __init__(self, store: ApprovalStore, notifier: Notifier):
        self.store = store
        self.notifier = notifier

    async def request_approval(self, order: OrderRequest, requester: str) -> ApprovalToken:
        token = ApprovalToken(
            order_id=order.order_id,
            requested_by=requester,
            required_approvers=2 if order.trading_mode == TradingMode.LIVE else 1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        await self.store.save(token)
        await self.notifier.notify_approvers(token)
        return token

    async def approve(self, token_id: ULID, approver: str) -> ApprovalStatus:
        token = await self.store.get(token_id)
        if approver in token.approved_by:
            raise ValueError("Already approved by this user")
        token.approved_by.append(approver)
        if len(token.approved_by) >= token.required_approvers:
            token.status = ApprovalStatus.APPROVED
        await self.store.save(token)
        return token.status

    async def wait_for_approval(self, token_id: ULID, timeout: float = 900) -> ApprovalStatus:
        # Poll or wait for notification
        pass


# Integration with risk engine:
async def evaluate(self, context: RiskContext) -> RiskResult:
    # ... risk checks ...
    if context.trading_mode == TradingMode.LIVE and context.requires_live_approval:
        token = await self.confirmation_bus.request_approval(context.order, context.user)
        status = await self.confirmation_bus.wait_for_approval(token.token_id)
        if status != ApprovalStatus.APPROVED:
            return RiskResult(rejected=True, reason="Approval denied or expired")
    return RiskResult(allowed=True)
```

### 25. Telemetry/Billing Events (P1)
**gemini-cli**: `telemetry/` with structured events, billing tracking

**zksato Application**: Trading audit events, compliance logging
```python
# zksato-core/src/zksato_core/telemetry.py
from opentelemetry import trace
from pydantic import BaseModel
from datetime import datetime
import json


class TradingEvent(BaseModel):
    event_id: ULID
    event_type: TradingEventType
    timestamp: datetime
    account_id: str
    correlation_id: ULID | None = None
    payload: dict


class TradingEventType(Enum):
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_REJECTED = "order.rejected"
    ORDER_CANCELLED = "order.cancelled"
    RISK_CHECK = "risk.check"
    RISK_OVERRIDE = "risk.override"
    RECONCILIATION_DRIFT = "reconciliation.drift"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    PNL_REALIZED = "pnl.realized"


class TelemetryLogger:
    def __init__(self, exporter: TelemetryExporter):
        self.exporter = exporter
        self.tracer = trace.get_tracer("zksato.telemetry")

    async def log(self, event: TradingEvent) -> None:
        # Structured logging
        logger.info("trading_event", extra=event.model_dump())

        # OpenTelemetry span
        with self.tracer.start_as_current_span(f"trading.{event.event_type.value}") as span:
            span.set_attribute("account_id", event.account_id)
            span.set_attribute("event_type", event.event_type.value)
            for k, v in event.payload.items():
                span.set_attribute(f"payload.{k}", str(v))

        # Export to audit store
        await self.exporter.export(event)

    # Convenience methods
    async def log_order_placed(self, order: OrderRequest, result: OrderResult) -> None:
        await self.log(
            TradingEvent(
                event_type=TradingEventType.ORDER_PLACED,
                account_id=order.account_id,
                correlation_id=order.correlation_id,
                payload={
                    "order_id": str(result.order_id),
                    "symbol": order.symbol,
                    "side": order.side.value,
                },
            )
        )

    async def log_risk_check(self, context: RiskContext, result: RiskResult) -> None:
        await self.log(
            TradingEvent(
                event_type=TradingEventType.RISK_CHECK,
                account_id=context.account_id,
                correlation_id=context.correlation_id,
                payload={
                    "allowed": result.allowed,
                    "reason": result.reason,
                    "checks": [c.model_dump() for c in result.checks],
                },
            )
        )
```

---

## Implementation Priority Matrix

| Phase | Patterns | Effort | Impact | Dependencies |
|-------|----------|--------|--------|--------------|
| 1 | 1, 2, 15 | High | Foundation | None |
| 2 | 3, 21, 24 | Medium | Risk safety | Phase 1 |
| 3 | 4, 5, 18, 19, 20 | High | Automation core | Phase 1 |
| 4 | 6, 7, 22, 23 | Medium | Extensibility | Phase 1, 3 |
| 5 | 8, 9, 11 | Medium | Observability | Phase 1 |
| 6 | 14, 10, 12 | Medium | DX, Resilience | Phase 3 |
| 7 | 13, 16, 17 | Low | Advanced | Phase 3, 5 |

---

## Anti-Patterns to Avoid

| gemini-cli Pattern | Why Not for zksato | Alternative |
|-------------------|-------------------|-------------|
| React/ink for CLI | Python ecosystem, operators prefer standard CLI | Typer + Rich |
| TypeScript types | Python codebase | Pydantic models |
| LLM-based agents | Deterministic trading required | Rule-based agents with LLM research only |
| Browser automation | No browser needed for trading | Native API/WebSocket |
| GitHub-specific extensions | Trading platform, not code agent | Trading skill plugins |
| OAuth for MCP | Broker APIs use API keys | API key / secret management |
| Conversation checkpointing | Trading sessions need event sourcing | Event-sourced session state |

---

## Decision Log Template (ADR)

When implementing each pattern, create an ADR:

```markdown
# ADR-XXX: [Pattern Name]

## Status
Proposed | Accepted | Superseded

## Context
Why this pattern from gemini-cli applies to zksato

## Decision
What we're implementing, how it maps

## Consequences
- Positive: 
- Negative:
- Risks:

## Implementation Notes
- Package:
- Key files:
- Tests:
- Migration:
```

---

*This document maps gemini-cli patterns to zksato upgrade opportunities. Update as patterns are adopted or rejected.*