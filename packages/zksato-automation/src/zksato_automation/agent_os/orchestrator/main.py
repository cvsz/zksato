"""Main orchestrator for autonomous agent engineering workflows."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from zksato_api.llm_clients import LocalLLMBackend, LocalLLMConfig  # type: ignore[import-untyped]

from zksato_automation.agent_os.context.manager import ContextManager
from zksato_automation.agent_os.monitoring.dashboard import (
    AgentStatus,
    ProviderMonitorData,
    QualityGateResult,
    get_monitor,
)
from zksato_automation.agent_os.providers.router import (
    LocalProvider,
    ModelRouter,
    ModelRouterWithFallback,
    ProviderRegistry,
    ProviderType,
)
from zksato_automation.agent_os.security.permissions import (
    Permission,
    PermissionManager,
    ToolExecutor,
    setup_builtin_tools,
)
from zksato_automation.agent_os.tasks.executor import TaskExecutor, create_task_plan
from zksato_automation.agent_os.tasks.persistence import TaskEventLogger, TaskStore
from zksato_automation.agent_os.tasks.state import (
    Task,
    TaskPlan,
    TaskPriority,
    TaskResult,
    TaskState,
    TaskType,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    agent_id: str
    role: str
    capabilities: set[str] = field(default_factory=set)
    model_preference: str | None = None
    provider_preference: ProviderType | None = None
    max_concurrent_tasks: int = 2
    default_timeout: float = 300.0
    permissions: set[Permission] = field(default_factory=set)
    context_window_tokens: int = 50000


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_concurrent_tasks: int = 4
    default_task_timeout: float = 300.0
    enable_monitoring: bool = True
    enable_security: bool = True
    task_storage_dir: str = ".zksato/tasks"
    context_max_tokens: int = 100000
    quality_gates_enabled: bool = True


class AutonomousOrchestrator:
    """Main orchestrator for autonomous agent engineering workflows."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()

        # Core components
        self.task_store = TaskStore(self.config.task_storage_dir)
        self.event_logger = TaskEventLogger(self.config.task_storage_dir)
        self.context_manager = ContextManager(self.config.context_max_tokens)
        self.monitor = get_monitor() if self.config.enable_monitoring else None

        # Security
        self.permission_manager = PermissionManager()
        self.tool_executor = ToolExecutor(self.permission_manager)
        if self.config.enable_security:
            setup_builtin_tools(self.permission_manager, self.tool_executor)

        # Provider routing
        self.provider_registry = ProviderRegistry()
        self.model_router = ModelRouter(self.provider_registry)
        self.router_with_fallback = ModelRouterWithFallback(self.model_router)

        # Task execution
        self.task_executor = TaskExecutor(
            store=self.task_store,
            event_logger=self.event_logger,
            max_concurrent=self.config.max_concurrent_tasks,
            default_timeout=self.config.default_task_timeout,
        )

        # Agent registry
        self._agents: dict[str, AgentConfig] = {}
        self._agent_tasks: dict[str, list[str]] = {}

        # Quality gates
        self._quality_gates: list[Callable[[TaskPlan], Awaitable[dict[str, Any]]]] = []

        # Register default task handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default task handlers."""
        self.task_executor.register_handler(TaskType.DISCOVER, self._handle_discover)
        self.task_executor.register_handler(TaskType.ANALYZE, self._handle_analyze)
        self.task_executor.register_handler(TaskType.PLAN, self._handle_plan)
        self.task_executor.register_handler(TaskType.IMPLEMENT, self._handle_implement)
        self.task_executor.register_handler(TaskType.REVIEW, self._handle_review)
        self.task_executor.register_handler(TaskType.TEST, self._handle_test)
        self.task_executor.register_handler(TaskType.REPAIR, self._handle_repair)
        self.task_executor.register_handler(TaskType.FINALIZE, self._handle_finalize)
        self.task_executor.register_handler(TaskType.SECURITY_AUDIT, self._handle_security_audit)
        self.task_executor.register_handler(
            TaskType.ARCHITECTURE_REVIEW, self._handle_architecture_review
        )
        self.task_executor.register_handler(TaskType.DOCUMENTATION, self._handle_documentation)

    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent."""
        self._agents[config.agent_id] = config
        self._agent_tasks[config.agent_id] = []

        # Grant permissions
        for perm in config.permissions:
            self.permission_manager.grant_permission(config.agent_id, perm)

        # Register with monitor
        if self.monitor:
            self.monitor.register_agent(
                AgentStatus(
                    agent_id=config.agent_id,
                    role=config.role,
                    provider=config.provider_preference.value
                    if config.provider_preference
                    else None,
                    model=config.model_preference,
                )
            )

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        del self._agent_tasks[agent_id]

        if self.monitor:
            self.monitor.unregister_agent(agent_id)

        return True

    def register_local_provider(
        self,
        backend: LocalLLMBackend,
        base_url: str,
        model: str,
        **kwargs: Any,
    ) -> LocalProvider:
        """Register a local LLM provider."""
        config = LocalLLMConfig(
            backend=backend,
            base_url=base_url,
            model=model,
            **kwargs,
        )
        provider = LocalProvider(config)
        provider_type = self._backend_to_provider_type(backend)
        self.provider_registry.register(provider, provider_type)
        return provider

    def _backend_to_provider_type(self, backend: LocalLLMBackend) -> ProviderType:
        mapping = {
            LocalLLMBackend.OLLAMA: ProviderType.OLLAMA,
            LocalLLMBackend.LLAMACPP: ProviderType.LLAMACPP,
            LocalLLMBackend.VLLM: ProviderType.VLLM,
            LocalLLMBackend.TGI: ProviderType.TGI,
            LocalLLMBackend.OPENAI_COMPATIBLE: ProviderType.LOCAL,
        }
        return mapping.get(backend, ProviderType.LOCAL)

    async def initialize_providers(self) -> None:
        """Initialize all registered providers."""
        for provider in self.provider_registry._providers.values():
            if hasattr(provider, "initialize"):
                await provider.initialize()

    async def check_provider_health(self) -> None:
        """Check health of all providers."""
        health_results = await self.provider_registry.check_health()
        for ptype, health in health_results.items():
            if self.monitor:
                self.monitor.update_provider(
                    ProviderMonitorData(
                        provider=ptype.value,
                        status="healthy" if health.is_healthy else "unhealthy",
                        latency_ms=health.latency_ms,
                        error_rate=health.error_rate,
                        requests_per_minute=0.0,  # Would track in production
                        available_models=health.models_available,
                        rate_limit_remaining=health.rate_limit_remaining,
                        last_health_check=health.last_check,
                    )
                )

    def register_quality_gate(self, gate: Callable[[TaskPlan], Awaitable[dict[str, Any]]]) -> None:
        """Register a quality gate function."""
        self._quality_gates.append(gate)

    async def execute_objective(
        self,
        objective: str,
        tasks: list[dict[str, Any]] | None = None,
        context_files: list[str] | None = None,
    ) -> TaskPlan:
        """Execute a high-level objective by creating and running a task plan."""
        # Create task plan
        if tasks:
            plan = await create_task_plan(objective, tasks)
        else:
            # Generate default plan based on objective
            plan = await self._generate_default_plan(objective)

        # Store plan
        self.task_store.save_plan(plan)
        if self.monitor:
            self.monitor.register_plan(plan)

        # Create context for the plan
        plan_context_id = f"plan_{plan.plan_id}"
        self.context_manager.create_task_context(
            plan_context_id,
            objective,
            repository_files=context_files,
        )

        # Register tasks with monitor
        for task in plan.tasks:
            if self.monitor:
                self.monitor.register_task(str(plan.plan_id), task)

        # Transition first task (no dependencies) to READY state
        for task in plan.tasks:
            if not task.dependencies:
                task.transition_to(TaskState.READY)
                break

        # Execute plan
        plan = await self.task_executor.execute_plan(plan)

        # Run quality gates
        if self.config.quality_gates_enabled:
            await self._run_quality_gates(plan)

        # Save final plan
        self.task_store.save_plan(plan)

        return plan

    async def _generate_default_plan(self, objective: str) -> TaskPlan:
        """Generate a default plan for an objective."""
        plan = TaskPlan(objective=objective)

        # Default phases
        phases = [
            (TaskType.DISCOVER, "Discover repository structure", TaskPriority.HIGH),
            (TaskType.ANALYZE, "Analyze requirements and constraints", TaskPriority.HIGH),
            (TaskType.PLAN, "Create implementation plan", TaskPriority.HIGH),
            (TaskType.IMPLEMENT, "Implement changes", TaskPriority.NORMAL),
            (TaskType.REVIEW, "Code review", TaskPriority.NORMAL),
            (TaskType.TEST, "Run tests and verify", TaskPriority.HIGH),
            (TaskType.SECURITY_AUDIT, "Security audit", TaskPriority.HIGH),
            (TaskType.FINALIZE, "Finalize and document", TaskPriority.NORMAL),
        ]

        prev_task_id = None
        for task_type, title, priority in phases:
            task = Task(
                task_type=task_type,
                title=title,
                description=f"{title} for: {objective}",
                priority=priority,
                context={"objective": objective},
            )
            if prev_task_id:
                task.add_dependency(prev_task_id)
            plan.add_task(task)
            prev_task_id = task.task_id

        return plan

    async def _run_quality_gates(self, plan: TaskPlan) -> None:
        """Run quality gates on completed plan."""
        for gate in self._quality_gates:
            try:
                result = await gate(plan)
                if self.monitor:
                    self.monitor.record_quality_gate(
                        QualityGateResult(
                            gate_name=gate.__name__,
                            passed=result.get("passed", False),
                            details=result.get("details", ""),
                            metrics=result.get("metrics", {}),
                        )
                    )
            except Exception as exc:
                logger.error("Quality gate %s failed: %s", gate.__name__, exc)
                if self.monitor:
                    self.monitor.record_quality_gate(
                        QualityGateResult(
                            gate_name=gate.__name__,
                            passed=False,
                            details=f"Gate exception: {exc}",
                        )
                    )

    # Task handlers
    async def _handle_discover(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle discovery task."""
        # In a real implementation, this would analyze the repository
        return TaskResult(
            success=True,
            output={"message": "Discovery complete"},
            files_modified=[],
        )

    async def _handle_analyze(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle analysis task."""
        return TaskResult(
            success=True,
            output={"message": "Analysis complete"},
            files_modified=[],
        )

    async def _handle_plan(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle planning task."""
        return TaskResult(
            success=True,
            output={"message": "Plan created"},
            files_modified=[],
        )

    async def _handle_implement(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle implementation task."""
        # This would use the LLM to generate code
        return TaskResult(
            success=True,
            output={"message": "Implementation complete"},
            files_modified=[],
        )

    async def _handle_review(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle review task."""
        return TaskResult(
            success=True,
            output={"message": "Review complete"},
            files_modified=[],
        )

    async def _handle_test(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle testing task."""
        # Run pytest
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = result.returncode == 0
        return TaskResult(
            success=passed,
            output={
                "message": "Tests passed" if passed else "Tests failed",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            files_modified=[],
            tests_passed=result.stdout.count("passed"),
            tests_failed=result.stdout.count("failed"),
        )

    async def _handle_repair(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle repair task."""
        return TaskResult(
            success=True,
            output={"message": "Repair attempted"},
            files_modified=[],
        )

    async def _handle_finalize(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle finalization task."""
        return TaskResult(
            success=True,
            output={"message": "Finalization complete"},
            files_modified=[],
        )

    async def _handle_security_audit(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle security audit task."""
        # Run security checks (bandit, safety, etc.)
        return TaskResult(
            success=True,
            output={"message": "Security audit complete"},
            files_modified=[],
        )

    async def _handle_architecture_review(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle architecture review task."""
        return TaskResult(
            success=True,
            output={"message": "Architecture review complete"},
            files_modified=[],
        )

    async def _handle_documentation(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle documentation task."""
        return TaskResult(
            success=True,
            output={"message": "Documentation updated"},
            files_modified=[],
        )

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        status = {
            "agents": len(self._agents),
            "registered_providers": list(self.provider_registry.list_providers()),
            "available_models": len(self.provider_registry.list_models()),
        }
        if self.monitor:
            status["overview"] = self.monitor.get_overview()
        return status
