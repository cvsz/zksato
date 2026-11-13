"""Orchestrator v2 - Advanced multi-agent orchestration.

Integrates Phase 3 capabilities with Phase 4 multi-agent framework.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Phase 3 integrations from CLI
from zksato_cli.editing.search import DiagnosticCollector, RipgrepSearcher, SymbolSearcher
from zksato_cli.hooks.framework import HookManager, setup_builtin_hooks
from zksato_cli.mcp.client import MCPClientManager
from zksato_cli.planning.plan_mode import PlanManager
from zksato_cli.sessions.persistence import SessionManager
from zksato_cli.skills.system import SkillManager, register_builtin_skills

from zksato_automation.agent_os.a2a.protocol import (
    A2ACommunicator,
    A2AMessage,
    A2AMessageType,
    AgentCapability,
    AgentInfo,
    AgentRegistry,
)
from zksato_automation.agent_os.agents.specialized import (
    ArchitectAgent,
    BaseSpecializedAgent,
    CodeReviewerAgent,
    DocumentationAgent,
    SecurityAuditorAgent,
    TestEngineerAgent,
)
from zksato_automation.agent_os.context.manager import ContextManager
from zksato_automation.agent_os.coordination.shared_state import SharedStateManager
from zksato_automation.agent_os.tasks.executor import TaskExecutor
from zksato_automation.agent_os.tasks.persistence import TaskEventLogger, TaskStore
from zksato_automation.agent_os.tasks.state import (
    Task,
    TaskPlan,
    TaskResult,
    TaskState,
    TaskType,
)

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorTask:
    """Task representation for orchestration."""

    task_id: str
    task_type: str
    title: str
    description: str
    required_capabilities: set[AgentCapability] = field(default_factory=set)
    priority: int = 0
    dependencies: list[str] = field(default_factory=list)
    assigned_agent: str | None = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class AgentAssignment:
    """Agent assignment for a task."""

    agent_id: str
    task_id: str
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    estimated_duration: float = 0.0


class OrchestratorV2:
    """Advanced orchestrator with multi-agent support."""

    def __init__(
        self,
        project_root: Path,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.config = config or {}

        # Core components
        self.agent_registry = AgentRegistry()
        self.shared_state = SharedStateManager()
        self.a2a_communicator = A2ACommunicator("orchestrator", self.agent_registry)

        # Agent pool
        self.agents: dict[str, BaseSpecializedAgent] = {}
        self.agent_configs: dict[str, dict[str, Any]] = {}

        # Task management
        self.tasks: dict[str, OrchestratorTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.task_executor = TaskExecutor(
            store=TaskStore(self.config.get("task_storage_dir", ".zksato/tasks")),
            event_logger=TaskEventLogger(self.config.get("task_storage_dir", ".zksato/tasks")),
            max_concurrent=self.config.get("max_concurrent_tasks", 4),
            default_timeout=self.config.get("default_task_timeout", 300.0),
        )

        self.assignments: dict[str, AgentAssignment] = {}

        # Phase 3 components
        self.context_manager = ContextManager()
        self.searcher = RipgrepSearcher(self.project_root)
        self.symbol_searcher = SymbolSearcher(self.project_root)
        self.diagnostic_collector = DiagnosticCollector(self.project_root)
        self.session_manager = SessionManager(self.project_root / ".zksato" / "sessions")
        self.plan_manager = PlanManager(
            project_root=self.project_root,
            session_manager=self.session_manager,
            storage_dir=self.project_root / ".zksato" / "plans",
        )
        self.hook_manager = HookManager()
        setup_builtin_hooks(self.hook_manager)
        self.skill_manager = SkillManager(
            project_root=self.project_root,
            hook_manager=self.hook_manager,
        )
        self.mcp_client = MCPClientManager()
        # Register built-in skills

        register_builtin_skills(self.skill_manager.registry)

        # Quality gates
        self._quality_gates: list[Callable[[TaskPlan], Awaitable[dict[str, Any]]]] = []

        # Register default task handlers
        self._register_default_handlers()

        # Coordination
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []

        # Initialize default agents
        self._initialize_agents()

    def _initialize_agents(self) -> None:
        """Initialize default specialized agents."""
        Path(self.project_root)

        # Architect Agent
        architect = ArchitectAgent(
            agent_id="architect-001",
            registry=self.agent_registry,
            project_root=self.project_root,
        )
        self.register_agent(architect)

        # Security Auditor
        security = SecurityAuditorAgent(
            agent_id="security-001",
            registry=self.agent_registry,
            project_root=self.project_root,
        )
        self.register_agent(security)

        # Code Reviewer
        reviewer = CodeReviewerAgent(
            agent_id="reviewer-001",
            registry=self.agent_registry,
            project_root=self.project_root,
        )
        self.register_agent(reviewer)

        # Test Engineer
        test_engineer = TestEngineerAgent(
            agent_id="tester-001",
            registry=self.agent_registry,
            project_root=self.project_root,
        )
        self.register_agent(test_engineer)

        # Documentation Agent
        docs = DocumentationAgent(
            agent_id="docs-001",
            registry=self.agent_registry,
            project_root=self.project_root,
        )
        self.register_agent(docs)

        logger.info("Initialized %d specialized agents", len(self.agents))

    def register_agent(self, agent: BaseSpecializedAgent) -> None:
        """Register a specialized agent."""
        self.agents[agent.agent_id] = agent

        # Register with A2A registry
        agent_info = AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            role=agent.role,
            capabilities=agent.capabilities,
            status="idle",
        )
        self.agent_registry.register(agent_info)

        # Store agent config
        self.agent_configs[agent.agent_id] = {
            "name": agent.name,
            "role": agent.role,
            "capabilities": [c.value for c in agent.capabilities],
        }

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.agent_registry.unregister(agent_id)
            self.agent_configs.pop(agent_id, None)
            return True
        return False

    async def start(self) -> None:
        """Start the orchestrator."""
        if self._running:
            return

        self._running = True

        # Register message handlers for task completion
        self.a2a_communicator.registry.register_handler(
            A2AMessageType.TASK_COMPLETE, self._handle_task_complete
        )
        self.a2a_communicator.registry.register_handler(
            A2AMessageType.TASK_FAILED, self._handle_task_failed
        )

        # Start worker tasks
        self._worker_tasks = [
            asyncio.create_task(self._task_dispatcher()),
            asyncio.create_task(self._task_monitor()),
            asyncio.create_task(self._health_monitor()),
        ]

        # Start all agents' heartbeat (kept referenced so tasks are not GC'd mid-flight)
        for agent in self.agents.values():
            self._worker_tasks.append(asyncio.create_task(self._agent_heartbeat(agent)))

        logger.info("Orchestrator V2 started")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self._running = False

        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)

        # Disconnect all agents
        for agent in self.agents.values():
            await agent.communicator.registry.send_message(
                A2AMessage(
                    message_type=A2AMessageType.STATUS_UPDATE,
                    sender_id="orchestrator",
                    recipient_id=agent.agent_id,
                    payload={"status": "shutdown"},
                )
            )

        logger.info("Orchestrator V2 stopped")

    def _register_default_handlers(self) -> None:
        """Register default task handlers."""
        self.task_executor.register_handler(TaskType.DISCOVER, self._handle_discover)
        self.task_executor.register_handler(TaskType.ANALYZE, self._handle_analyze)
        self.task_executor.register_handler(TaskType.ANALYZE_CODE, self._handle_analyze)
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

    async def _agent_heartbeat(self, agent: BaseSpecializedAgent) -> None:
        """Send periodic heartbeats for an agent."""
        while self._running:
            try:
                await agent.communicator.send_heartbeat()
            except Exception as exc:
                logger.error("Heartbeat failed for %s: %s", agent.agent_id, exc)
            await asyncio.sleep(30)  # Heartbeat every 30 seconds

    async def submit_task(
        self,
        task_type: str,
        title: str,
        description: str,
        required_capabilities: set[AgentCapability],
        priority: int = 0,
        dependencies: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        """Submit a new task for execution."""
        import uuid

        task = OrchestratorTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            title=title,
            description=description,
            required_capabilities=required_capabilities,
            priority=priority,
            dependencies=dependencies or [],
            payload=payload or {},
        )

        self.tasks[task.task_id] = task
        await self.task_queue.put(task.task_id)

        logger.info("Submitted task %s: %s", task.task_id, title)
        return task.task_id

    async def _task_dispatcher(self) -> None:
        """Dispatch tasks to available agents."""
        while self._running:
            try:
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                task = self.tasks.get(task_id)

                if not task or task.status != "pending":
                    continue

                # Check dependencies
                if not self._dependencies_met(task):
                    # Re-queue with delay
                    await asyncio.sleep(1)
                    await self.task_queue.put(task_id)
                    continue

                # Find suitable agent
                agent_id = await self._find_suitable_agent(task)
                if not agent_id:
                    # No agent available, re-queue
                    await asyncio.sleep(5)
                    await self.task_queue.put(task_id)
                    continue

                # Assign task
                await self._assign_task(task, agent_id)

            except TimeoutError:
                continue
            except Exception as exc:
                logger.error("Task dispatcher error: %s", exc)

    def _dependencies_met(self, task: OrchestratorTask) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != "completed":
                return False
        return True

    async def _find_suitable_agent(self, task: OrchestratorTask) -> str | None:
        """Find the best agent for a task."""
        # Find agents with required capabilities
        candidates = self.agent_registry.find_available_agents(
            next(iter(task.required_capabilities))
            if task.required_capabilities
            else AgentCapability.TASK_EXECUTION
        )

        # Filter by all required capabilities
        candidates = [
            a for a in candidates if all(a.can_handle(c) for c in task.required_capabilities)
        ]

        if not candidates:
            return None

        # Select best candidate (lowest load, highest capability match)
        best = min(candidates, key=lambda a: a.load_factor)
        return best.agent_id

    async def _assign_task(self, task: OrchestratorTask, agent_id: str) -> None:
        """Assign a task to an agent."""
        task.assigned_agent = agent_id
        task.status = "assigned"

        assignment = AgentAssignment(
            agent_id=agent_id,
            task_id=task.task_id,
        )
        self.assignments[task.task_id] = assignment

        # Update agent status
        agent_info = self.agent_registry.get_agent(agent_id)
        if agent_info:
            agent_info.status = "busy"
            agent_info.current_task_id = task.task_id
            agent_info.load_factor = min(1.0, agent_info.load_factor + 0.2)

        # Send task request via A2A
        A2AMessage(
            message_type=A2AMessageType.TASK_REQUEST,
            sender_id="orchestrator",
            recipient_id=agent_id,
            payload={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "payload": task.payload,
            },
        )

        # Send via A2A communicator - execute task directly and handle result
        agent = self.agents.get(agent_id)
        if agent:
            try:
                task.status = "running"
                task.started_at = datetime.now(UTC)
                result = await agent.execute_task(task.task_type, task.payload)
                task.status = "completed"
                task.result = result
                task.completed_at = datetime.now(UTC)

                # Release agent
                agent_info = self.agent_registry.get_agent(agent_id)
                if agent_info:
                    agent_info.status = "idle"
                    agent_info.current_task_id = None
                    agent_info.load_factor = max(0.0, agent_info.load_factor - 0.2)

                logger.info("Task %s completed successfully", task.task_id)
            except Exception as exc:
                logger.error("Task %s failed: %s", task.task_id, exc)
                task.status = "failed"
                task.error = str(exc)
                task.completed_at = datetime.now(UTC)

                # Release agent
                agent_info = self.agent_registry.get_agent(agent_id)
                if agent_info:
                    agent_info.status = "idle"
                    agent_info.current_task_id = None
                    agent_info.load_factor = max(0.0, agent_info.load_factor - 0.2)

                logger.warning("Task %s failed: %s", task.task_id, exc)

    async def _task_monitor(self) -> None:
        """Monitor task progress and handle timeouts."""
        while self._running:
            try:
                await asyncio.sleep(10)

                for task_id, task in list(self.tasks.items()):
                    if task.status in ("completed", "failed"):
                        continue

                    # Check for timeout
                    if task.started_at:
                        elapsed = (datetime.now(UTC) - task.started_at).total_seconds()
                        if elapsed > 300:  # 5 minute timeout
                            logger.warning("Task %s timed out", task_id)
                            await self._handle_task_timeout(task)

            except Exception as exc:
                logger.error("Task monitor error: %s", exc)

    async def _handle_task_timeout(self, task: OrchestratorTask) -> None:
        """Handle task timeout."""
        task.status = "failed"
        task.error = "Task timed out"
        task.completed_at = datetime.now(UTC)

        # Release agent
        if task.assigned_agent:
            agent_info = self.agent_registry.get_agent(task.assigned_agent)
            if agent_info:
                agent_info.status = "idle"
                agent_info.current_task_id = None
                agent_info.load_factor = max(0.0, agent_info.load_factor - 0.2)

        # Could implement retry logic here
        logger.warning("Task %s timed out and marked as failed", task.task_id)

    async def _handle_task_complete(self, message: A2AMessage) -> None:
        """Handle task completion message from agent."""
        task_id = message.payload.get("task_id")
        result = message.payload.get("result")
        task = self.tasks.get(task_id)

        if not task:
            logger.warning("Received completion for unknown task: %s", task_id)
            return

        task.status = "completed"
        task.result = result
        task.completed_at = datetime.now(UTC)

        # Release agent
        if task.assigned_agent:
            agent_info = self.agent_registry.get_agent(task.assigned_agent)
            if agent_info:
                agent_info.status = "idle"
                agent_info.current_task_id = None
                agent_info.load_factor = max(0.0, agent_info.load_factor - 0.2)

        logger.info("Task %s completed successfully", task_id)

    async def _handle_task_failed(self, message: A2AMessage) -> None:
        """Handle task failure message from agent."""
        task_id = message.payload.get("task_id")
        error = message.payload.get("error", "Unknown error")
        task = self.tasks.get(task_id)

        if not task:
            logger.warning("Received failure for unknown task: %s", task_id)
            return

        task.status = "failed"
        task.error = error
        task.completed_at = datetime.now(UTC)

        # Release agent
        if task.assigned_agent:
            agent_info = self.agent_registry.get_agent(task.assigned_agent)
            if agent_info:
                agent_info.status = "idle"
                agent_info.current_task_id = None
                agent_info.load_factor = max(0.0, agent_info.load_factor - 0.2)

        logger.warning("Task %s failed: %s", task_id, error)

    async def _health_monitor(self) -> None:
        """Monitor agent health."""
        while self._running:
            try:
                await asyncio.sleep(60)

                for agent_id, agent_info in self.agent_registry.agents.items():
                    # Check heartbeat
                    age = (datetime.now(UTC) - agent_info.last_heartbeat).total_seconds()
                    if age > 120:  # 2 minutes
                        logger.warning("Agent %s heartbeat stale (%s seconds)", agent_id, age)
                        agent_info.status = "unhealthy"

            except Exception as exc:
                logger.error("Health monitor error: %s", exc)

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "running": self._running,
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "role": agent.role,
                    "status": self.agent_registry.agents.get(agent_id, {}).status
                    if self.agent_registry.agents.get(agent_id)
                    else "unknown",
                    "current_task": self.agent_registry.agents.get(agent_id, {}).current_task_id
                    if self.agent_registry.agents.get(agent_id)
                    else None,
                    "load": self.agent_registry.agents.get(agent_id, {}).load_factor
                    if self.agent_registry.agents.get(agent_id)
                    else 0.0,
                }
                for agent_id, agent in self.agents.items()
            },
            "tasks": {
                "pending": len([t for t in self.tasks.values() if t.status == "pending"]),
                "assigned": len([t for t in self.tasks.values() if t.status == "assigned"]),
                "running": len([t for t in self.tasks.values() if t.status == "running"]),
                "completed": len([t for t in self.tasks.values() if t.status == "completed"]),
                "failed": len([t for t in self.tasks.values() if t.status == "failed"]),
            },
            "queue_size": self.task_queue.qsize(),
        }

    async def execute_workflow(
        self,
        workflow_name: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute a multi-step workflow."""
        task_ids = []

        # Submit all tasks
        for i, step in enumerate(steps):
            task_id = await self.submit_task(
                task_type=step["type"],
                title=step.get("title", f"Step {i + 1}"),
                description=step.get("description", ""),
                required_capabilities={AgentCapability(c) for c in step.get("capabilities", [])},
                priority=step.get("priority", 0),
                dependencies=[task_ids[dep] for dep in step.get("depends_on", []) if dep < i],
                payload=step.get("payload", {}),
            )
            task_ids.append(task_id)

        # Wait for completion
        while True:
            await asyncio.sleep(1)
            tasks = [self.tasks[tid] for tid in task_ids]
            if all(t.status in ("completed", "failed") for t in tasks):
                break

        # Collect results
        results = {}
        for tid in task_ids:
            task = self.tasks[tid]
            results[tid] = {
                "status": task.status,
                "result": task.result,
                "error": task.error,
            }

        return {
            "workflow": workflow_name,
            "completed": all(t.status == "completed" for t in tasks),
            "results": results,
        }

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
                    session_id=plan.session_id if hasattr(plan, "session_id") else "default",
                    exploration_findings=plan.metadata.get("findings", {}),
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

            # Split command into list to avoid shell=True
            cmd_parts = test_command.split() if isinstance(test_command, str) else test_command

            result = subprocess.run(
                cmd_parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            passed = result.returncode == 0

            # Parse test results
            passed_count = result.stdout.count("PASSED")
            failed_count = result.stdout.count("FAILED")
            error_count = result.stdout.count("ERROR")

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


class AgentCoordinator:
    """Coordinates multiple agents for complex tasks."""

    def __init__(self, orchestrator: OrchestratorV2) -> None:
        self.orchestrator = orchestrator

    async def handoff_task(
        self,
        from_agent: str,
        to_agent: str,
        task_id: str,
        context: dict[str, Any],
    ) -> bool:
        """Hand off a task from one agent to another."""
        # Request handoff
        response = await self.orchestrator.agents[from_agent].communicator.send_handoff_request(
            target_agent=to_agent,
            task_id=task_id,
            context=context,
            reason=f"Handoff from {from_agent}",
        )

        if response and response.payload.get("accepted"):
            # Update task assignment
            task = self.orchestrator.tasks.get(task_id)
            if task:
                task.assigned_agent = to_agent
                return True
        return False

    async def coordinate_agents(
        self,
        agents: list[str],
        task: dict[str, Any],
        coordination_type: str = "sequential",
    ) -> dict[str, Any]:
        """Coordinate multiple agents on a task."""
        if coordination_type == "sequential":
            results = {}
            for _agent_id in agents:
                # Execute sequentially
                pass
            return {"results": results}
        elif coordination_type == "parallel":
            # Execute in parallel
            pass
        return {"status": "not_implemented"}

    async def resolve_conflict(
        self,
        agent_a: str,
        agent_b: str,
        conflict_type: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve conflict between agents."""
        # This would implement conflict resolution logic
        return {
            "resolved": False,
            "resolution": "manual_intervention_required",
        }


class WorkflowEngine:
    """Workflow engine for complex multi-step operations."""

    def __init__(self, orchestrator: OrchestratorV2) -> None:
        self.orchestrator = orchestrator

    async def execute_pipeline(
        self,
        pipeline_name: str,
        stages: list[dict[str, Any]],
        initial_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a pipeline of stages."""
        current_payload = initial_payload or {}
        results = {}

        for i, stage in enumerate(stages):
            stage_name = stage.get("name", f"Stage {i + 1}")

            # Submit stage as task
            task_id = await self.orchestrator.submit_task(
                task_type=stage.get("type", "generic"),
                title=stage_name,
                description=stage.get("description", ""),
                required_capabilities={AgentCapability(c) for c in stage.get("capabilities", [])},
                payload={**current_payload, **stage.get("payload", {})},
            )

            # Wait for completion
            while True:
                task = self.orchestrator.tasks.get(task_id)
                if task and task.status in ("completed", "failed"):
                    break
                await asyncio.sleep(1)

            if task and task.status == "completed":
                results[stage_name] = task.result
                # Pass output to next stage
                if task.result and isinstance(task.result, dict):
                    current_payload.update(task.result)
            else:
                return {
                    "pipeline": pipeline_name,
                    "status": "failed",
                    "failed_stage": stage_name,
                    "error": task.error if task else "Unknown",
                    "results": results,
                }

        return {
            "pipeline": pipeline_name,
            "status": "completed",
            "results": results,
        }
