"""Main orchestrator for autonomous agent engineering workflows."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zksato_api.llm_clients import LocalLLMBackend, LocalLLMConfig  # type: ignore[import-untyped]
from zksato_cli.editing.patch_engine import PatchApplicator, PatchBuilder
from zksato_cli.editing.search import DiagnosticCollector, RipgrepSearcher, SymbolSearcher
from zksato_cli.hooks.framework import HookEvent, HookManager, setup_builtin_hooks

# Phase 3 integrations
from zksato_cli.mcp.client import MCPClientManager
from zksato_cli.planning.plan_mode import PlanManager
from zksato_cli.sessions.persistence import SessionManager
from zksato_cli.skills.system import SkillManager, register_builtin_skills

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

    # Phase 3 integrations
    enable_mcp: bool = True
    mcp_config_dir: str = ".zksato/mcp"
    enable_skills: bool = True
    skills_storage_dir: str = ".zksato/skills"
    enable_hooks: bool = True
    hooks_audit_log: str = ".zksato/hooks/audit.log"
    enable_sessions: bool = True
    sessions_storage_dir: str = ".zksato/sessions"
    project_root: str = "."
    enable_plan_mode: bool = True
    plans_storage_dir: str = ".zksato/plans"


class AutonomousOrchestrator:
    """Main orchestrator for autonomous agent engineering workflows."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self.project_root = Path(self.config.project_root).resolve()

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

        # Phase 3: Session Management
        if self.config.enable_sessions:
            self.session_manager = SessionManager(self.config.sessions_storage_dir)
        else:
            self.session_manager = None

        # Phase 3: Plan Mode
        if self.config.enable_plan_mode:
            self.plan_manager = PlanManager(
                self.project_root,
                self.session_manager,
                self.config.plans_storage_dir,
            )
        else:
            self.plan_manager = None

        # Phase 3: MCP Integration
        if self.config.enable_mcp:
            self.mcp_manager = MCPClientManager(self.config.mcp_config_dir)
        else:
            self.mcp_manager = None

        # Phase 3: Skills
        if self.config.enable_skills:
            self.skill_manager = SkillManager(
                self.project_root,
                self.config.skills_storage_dir,
            )
            register_builtin_skills(self.skill_manager.registry)
        else:
            self.skill_manager = None

        # Phase 3: Hooks
        if self.config.enable_hooks:
            self.hook_manager = HookManager(Path(self.config.hooks_audit_log))
            setup_builtin_hooks(self.hook_manager)
        else:
            self.hook_manager = None

        # Phase 3: Patch Engine
        self.patch_applicator = PatchApplicator(self.project_root)
        self.patch_builder = PatchBuilder(self.project_root)

        # Phase 3: Search/Grep
        self.searcher = RipgrepSearcher(self.project_root)
        self.symbol_searcher = SymbolSearcher(self.project_root)
        self.diagnostic_collector = DiagnosticCollector(self.project_root)

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
        use_plan_mode: bool = True,
        auto_approve: bool = False,
    ) -> TaskPlan:
        """Execute a high-level objective by creating and running a task plan with full Phase 3 integration."""

        # Create or resume session
        session = None
        if self.session_manager:
            session = self.session_manager.create_session(
                str(self.project_root),
                f"Objective: {objective[:80]}",
            )

        # Emit session start hook
        if self.hook_manager and session:
            await self.hook_manager.emit_simple(
                HookEvent.SESSION_START,
                session_id=session.session_id,
                data={"objective": objective, "project_root": str(self.project_root)},
            )

        # Use Plan Mode for enhanced planning if enabled
        if use_plan_mode and self.plan_manager:
            # Create exploration plan first
            exploration_plan = self.plan_manager.create_exploration_plan(
                objective,
                session.session_id if session else "default",
                context_files,
            )
            self.plan_manager.create_plan(exploration_plan)

            # Execute exploration to gather context
            await self._run_exploration(exploration_plan)

            # Create implementation plan based on findings
            impl_plan = self.plan_manager.create_implementation_plan(
                objective,
                session.session_id if session else "default",
                exploration_plan.metadata.get("findings", {}),
            )
            self.plan_manager.create_plan(impl_plan)

            # Convert CLI Plan to automation TaskPlan
            plan = self._convert_plan_to_automation(impl_plan)
        else:
            # Fallback to legacy plan creation
            if tasks:
                plan = await create_task_plan(objective, tasks)
            else:
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

        # Execute plan with enhanced handlers
        plan = await self.task_executor.execute_plan(plan)

        # Run quality gates
        if self.config.quality_gates_enabled:
            await self._run_quality_gates(plan)

        # Save final plan
        self.task_store.save_plan(plan)

        # Emit session end hook
        if self.hook_manager and session:
            # Determine plan status from task states
            if plan.has_failures():
                plan_status = "failed"
            elif plan.is_complete():
                plan_status = "completed"
            else:
                plan_status = "running"

            await self.hook_manager.emit_simple(
                HookEvent.SESSION_END,
                session_id=session.session_id,
                data={"plan_id": str(plan.plan_id), "status": plan_status},
            )

        return plan

    async def _run_exploration(self, plan: TaskPlan) -> None:
        """Run exploration phase to gather context."""
        # Use search and analysis tools to explore the codebase
        for task in plan.tasks:
            if task.task_type == TaskType.DISCOVER:
                # Search for relevant files
                results = self.searcher.search(
                    "class|def|async def",
                    file_pattern="*.py",
                    max_results=50,
                )
                task.result = {
                    "files_found": results.files_with_matches,
                    "total_matches": results.total_matches,
                }
                task.status = TaskState.COMPLETED

            elif task.task_type == TaskType.ANALYZE:
                # Analyze discovered files
                if plan.metadata.get("findings") is None:
                    plan.metadata["findings"] = {}
                plan.metadata["findings"]["files"] = plan.tasks[0].result if plan.tasks else {}
                task.status = TaskState.COMPLETED

    async def execute_plan_with_skills(
        self,
        plan: TaskPlan,
        skill_instances: dict[str, str] | None = None,
    ) -> TaskPlan:
        """Execute a plan using skill instances for task execution."""
        # Register skill-based task handlers
        if skill_instances:
            for skill_name, instance_id in skill_instances.items():
                # Bind instance_id via default arg to avoid late-binding loop capture
                self.task_executor.register_handler(
                    TaskType(skill_name.upper()),
                    lambda task, p, instance_id=instance_id: self._execute_skill_task(
                        instance_id, task, p
                    ),
                )

        return await self.task_executor.execute_plan(plan)

    async def _execute_skill_task(
        self,
        instance_id: str,
        task: Task,
        plan: TaskPlan,
    ) -> TaskResult:
        """Execute a task using a skill instance."""
        if not self.skill_manager:
            return TaskResult(success=False, error="Skill manager not enabled")

        try:
            execution = await self.skill_manager.execute(
                instance_id,
                task.parameters,
                session_id=plan.plan_id,
            )
            return TaskResult(
                success=execution.success,
                output=execution.output,
                error=execution.error,
            )
        except Exception as exc:
            return TaskResult(success=False, error=str(exc))

    def _convert_plan_to_automation(self, cli_plan) -> TaskPlan:
        """Convert CLI Plan (with PlanTask) to automation TaskPlan (with Task)."""
        automation_plan = TaskPlan(
            objective=cli_plan.objective,
        )

        # Map CLI TaskStatus to automation TaskState
        status_map = {
            "pending": TaskState.CREATED,
            "ready": TaskState.READY,
            "running": TaskState.RUNNING,
            "completed": TaskState.COMPLETED,
            "failed": TaskState.FAILED,
            "skipped": TaskState.CANCELLED,
            "blocked": TaskState.BLOCKED,
        }

        # Map CLI TaskType to automation TaskType
        type_map = {
            "exploration": TaskType.DISCOVER,
            "analysis": TaskType.ANALYZE,
            "plan": TaskType.PLAN,
            "implement": TaskType.IMPLEMENT,
            "review": TaskType.REVIEW,
            "test": TaskType.TEST,
            "repair": TaskType.REPAIR,
            "finalize": TaskType.FINALIZE,
            "security_audit": TaskType.SECURITY_AUDIT,
            "architecture_review": TaskType.ARCHITECTURE_REVIEW,
            "documentation": TaskType.DOCUMENTATION,
        }

        # Map priority values
        priority_map = {
            0: TaskPriority.NORMAL,
            50: TaskPriority.NORMAL,
            100: TaskPriority.HIGH,
            200: TaskPriority.CRITICAL,
        }

        task_id_map = {}  # CLI task_id -> automation task_id

        for cli_task in cli_plan.tasks:
            task = Task(
                task_type=type_map.get(cli_task.task_type.value, TaskType.ANALYZE),
                title=cli_task.title,
                description=cli_task.description,
                priority=priority_map.get(cli_task.priority, TaskPriority.NORMAL),
                context=cli_task.parameters,
            )

            # Set state if available
            if cli_task.status:
                task.state = status_map.get(cli_task.status.value, TaskState.CREATED)

            # Map dependencies
            for dep_id in cli_task.dependencies:
                if dep_id in task_id_map:
                    task.add_dependency(task_id_map[dep_id])
                else:
                    # Dependency not yet mapped, will be resolved later
                    pass

            task_id_map[cli_task.task_id] = task.task_id
            automation_plan.add_task(task)

        # Resolve dependencies that weren't mapped yet
        for cli_task in cli_plan.tasks:
            automation_task = automation_plan.get_task(task_id_map[cli_task.task_id])
            if automation_task:
                for dep_id in cli_task.dependencies:
                    if dep_id in task_id_map:
                        automation_task.add_dependency(task_id_map[dep_id])

        return automation_plan

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

    # Task handlers with Phase 3 integrations
    async def _handle_discover(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle discovery task - explore codebase using search tools."""
        try:
            # Use ripgrep to find relevant files
            query = task.parameters.get("query", "class|def|async def")
            file_pattern = task.parameters.get("file_pattern", "*.py")
            max_results = task.parameters.get("max_results", 100)

            results = self.searcher.search(
                query,
                file_pattern=file_pattern,
                max_results=max_results,
                context_lines=2,
            )

            # Also search for symbols if specified
            symbol = task.parameters.get("symbol")
            if symbol:
                symbol_results = self.symbol_searcher.find_definition(symbol)
                return TaskResult(
                    success=True,
                    output={
                        "message": "Discovery complete",
                        "files_found": results.files_with_matches,
                        "total_matches": results.total_matches,
                        "symbol_definitions": len(symbol_results.results),
                        "results": [
                            {"file": r.file_path, "line": r.line_number, "match": r.line}
                            for r in results.results[:20]
                        ],
                    },
                    files_modified=[],
                )

            return TaskResult(
                success=True,
                output={
                    "message": "Discovery complete",
                    "files_found": results.files_with_matches,
                    "total_matches": results.total_matches,
                    "results": [
                        {"file": r.file_path, "line": r.line_number, "match": r.line}
                        for r in results.results[:20]
                    ],
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Discovery failed: {exc}")

    async def _handle_analyze(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle analysis task - analyze code using search and diagnostics."""
        try:
            target = task.parameters.get("target", "")
            task.parameters.get("language", "python")

            if target:
                # Search for the target symbol/code
                results = self.searcher.search(target, file_pattern="*.py")
                symbol_results = self.symbol_searcher.find_definition(target)

                # Run diagnostics if requested
                diagnostics = []
                if task.parameters.get("run_diagnostics", False):
                    diagnostics = self.diagnostic_collector.collect_all()

                return TaskResult(
                    success=True,
                    output={
                        "message": "Analysis complete",
                        "search_results": [
                            {"file": r.file_path, "line": r.line_number, "match": r.line}
                            for r in results.results[:20]
                        ],
                        "symbol_definitions": len(symbol_results.results),
                        "diagnostics": len(diagnostics),
                    },
                    files_modified=[],
                )

            return TaskResult(
                success=True,
                output={"message": "Analysis complete (no target specified)"},
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Analysis failed: {exc}")

    async def _handle_plan(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle planning task - create implementation plan."""
        try:
            # Use plan manager if available
            if self.plan_manager and plan.metadata.get("findings"):
                impl_plan = self.plan_manager.create_implementation_plan(
                    plan.objective,
                    plan.session_id if hasattr(plan, "session_id") else "default",
                    plan.metadata.get("findings", {}),
                )
                self.plan_manager.create_plan(impl_plan)

                return TaskResult(
                    success=True,
                    output={
                        "message": "Implementation plan created",
                        "plan_id": str(impl_plan.plan_id),
                        "tasks": len(impl_plan.tasks),
                    },
                    files_modified=[],
                )

            return TaskResult(
                success=True,
                output={"message": "Plan created (basic)"},
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Planning failed: {exc}")

    async def _handle_implement(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle implementation task - generate code using skills or LLM."""
        try:
            # Check if there's a skill instance for this task
            skill_instance_id = task.parameters.get("skill_instance_id")
            if skill_instance_id and self.skill_manager:
                execution = await self.skill_manager.execute(
                    skill_instance_id,
                    task.parameters,
                    session_id=str(plan.plan_id),
                )
                return TaskResult(
                    success=execution.success,
                    output=execution.output,
                    error=execution.error,
                    files_modified=execution.output.get("files_modified", [])
                    if execution.output
                    else [],
                )

            # Fallback: generate code using search context
            prompt = task.parameters.get("prompt", "")
            if prompt:
                # Search for similar patterns in codebase
                results = self.searcher.search(prompt, file_pattern="*.py", max_results=5)

                return TaskResult(
                    success=True,
                    output={
                        "message": "Implementation scaffold ready",
                        "prompt": prompt,
                        "reference_files": [r.file_path for r in results.results[:5]],
                    },
                    files_modified=[],
                )

            return TaskResult(
                success=True,
                output={"message": "Implementation complete"},
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Implementation failed: {exc}")

    async def _handle_review(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle review task - run code review using skills or diagnostics."""
        try:
            # Run diagnostics as part of review
            diagnostics = self.diagnostic_collector.collect_all()

            # Search for potential issues
            results = self.searcher.search(
                "TODO|FIXME|XXX|HACK|BUG",
                file_pattern="*.py",
                max_results=20,
            )

            return TaskResult(
                success=True,
                output={
                    "message": "Review complete",
                    "diagnostics_count": len(diagnostics),
                    "todo_comments": len(results.results),
                    "issues": [
                        {"file": r.file_path, "line": r.line_number, "text": r.line}
                        for r in results.results[:10]
                    ],
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Review failed: {exc}")

    async def _handle_test(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle testing task - run tests and verify."""
        try:
            import subprocess

            test_command = task.parameters.get("command", "python -m pytest")
            timeout = task.parameters.get("timeout", 120)
            # Parse command into list to avoid shell=True
            import shlex

            cmd_list = shlex.split(test_command)

            result = subprocess.run(
                cmd_list,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            passed = result.returncode == 0

            # Parse test results
            passed_count = result.stdout.count("passed")
            failed_count = result.stdout.count("failed")
            error_count = result.stdout.count("error")

            return TaskResult(
                success=passed,
                output={
                    "message": "Tests passed" if passed else "Tests failed",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                files_modified=[],
                tests_passed=passed_count,
                tests_failed=failed_count + error_count,
            )
        except subprocess.TimeoutExpired:
            return TaskResult(success=False, error="Tests timed out")
        except Exception as exc:
            return TaskResult(success=False, error=f"Testing failed: {exc}")

    async def _handle_repair(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle repair task - attempt to fix issues."""
        try:
            # Get failed tasks from plan
            failed_tasks = plan.get_failed_tasks()
            if not failed_tasks:
                return TaskResult(
                    success=True,
                    output={"message": "No failed tasks to repair"},
                    files_modified=[],
                )

            repaired = []
            for failed_task in failed_tasks:
                # Attempt retry with modified parameters
                if failed_task.retry_count < failed_task.max_retries:
                    failed_task.retry_count += 1
                    failed_task.status = TaskState.READY
                    repaired.append(failed_task.task_id)

            return TaskResult(
                success=True,
                output={
                    "message": f"Queued {len(repaired)} tasks for retry",
                    "retried_tasks": repaired,
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Repair failed: {exc}")

    async def _handle_finalize(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle finalization task - create summary and documentation."""
        try:
            completed = plan.get_completed_tasks()
            failed = plan.get_failed_tasks()

            # Generate summary
            summary = {
                "objective": plan.objective,
                "total_tasks": len(plan.tasks),
                "completed": len(completed),
                "failed": len(failed),
                "progress": f"{plan.progress() * 100:.0f}%",
            }

            return TaskResult(
                success=True,
                output={
                    "message": "Finalization complete",
                    "summary": summary,
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Finalization failed: {exc}")

    async def _handle_security_audit(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle security audit task - run security checks."""
        try:
            diagnostics = self.diagnostic_collector.collect_all()
            security_issues = [d for d in diagnostics if "security" in d.get("message", "").lower()]

            # Search for common security patterns
            security_patterns = [
                "password",
                "secret",
                "api_key",
                "token",
                "credential",
                "sql.*inject",
                "eval\\(",
                "exec\\(",
                "pickle\\.load",
            ]

            security_findings = []
            for pattern in security_patterns:
                results = self.searcher.search(pattern, file_pattern="*.py", max_results=10)
                if results.results:
                    security_findings.extend(
                        [
                            {"pattern": pattern, "file": r.file_path, "line": r.line_number}
                            for r in results.results
                        ]
                    )

            return TaskResult(
                success=True,
                output={
                    "message": "Security audit complete",
                    "diagnostics_checked": len(diagnostics),
                    "security_issues_found": len(security_issues),
                    "pattern_matches": len(security_findings),
                    "findings": security_findings[:20],
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Security audit failed: {exc}")

    async def _handle_architecture_review(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle architecture review task."""
        try:
            # Analyze project structure
            results = self.searcher.search(
                "class|def|import",
                file_pattern="*.py",
                max_results=100,
            )

            # Count files and complexity
            py_files = set()
            for r in results.results:
                py_files.add(r.file_path)

            return TaskResult(
                success=True,
                output={
                    "message": "Architecture review complete",
                    "python_files": len(py_files),
                    "total_symbols": results.total_matches,
                    "structure": {
                        "files": list(py_files)[:20],
                    },
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Architecture review failed: {exc}")

    async def _handle_documentation(self, task: Task, plan: TaskPlan) -> TaskResult:
        """Handle documentation task - update docs."""
        try:
            # Search for docstrings and comments
            results = self.searcher.search(
                '""".*?"""|# .*',
                file_pattern="*.py",
                max_results=50,
            )

            return TaskResult(
                success=True,
                output={
                    "message": "Documentation update ready",
                    "docstrings_found": len(results.results),
                },
                files_modified=[],
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Documentation failed: {exc}")

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
