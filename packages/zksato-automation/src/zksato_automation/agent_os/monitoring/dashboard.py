"""Real-time monitoring and dashboard for agent orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from zksato_automation.agent_os.tasks.state import Task, TaskPlan, TaskState, TaskType

logger = logging.getLogger(__name__)


@dataclass
class AgentStatus:
    """Agent status information."""

    agent_id: str
    role: str
    status: str = "idle"  # idle, running, blocked, error
    current_task_id: str | None = None
    provider: str | None = None
    model: str | None = None
    started_at: datetime | None = None
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskMonitorData:
    """Task monitoring data."""

    task_id: UUID
    plan_id: UUID
    title: str
    task_type: TaskType
    state: TaskState
    priority: int
    assigned_agent: str | None
    progress: float = 0.0
    retry_count: int = 0
    started_at: datetime | None = None
    estimated_completion: datetime | None = None
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)


@dataclass
class ProviderMonitorData:
    """Provider monitoring data."""

    provider: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float
    error_rate: float
    requests_per_minute: float
    available_models: list[str]
    rate_limit_remaining: int | None
    last_health_check: datetime


@dataclass
class QualityGateResult:
    """Quality gate result."""

    gate_name: str
    passed: bool
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metrics: dict[str, Any] = field(default_factory=dict)


class OrchestrationMonitor:
    """Real-time orchestration monitor with performance metrics."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentStatus] = {}
        self.tasks: dict[str, TaskMonitorData] = {}
        self.plans: dict[str, TaskPlan] = {}
        self.providers: dict[str, ProviderMonitorData] = {}
        self.quality_gates: list[QualityGateResult] = []
        self._event_listeners: list[Callable[[str, Any], None]] = []
        self._lock = asyncio.Lock()

        # Performance metrics
        self.metrics: dict[str, Any] = {
            "cold_start_ms": 0,
            "task_dispatch_latency_ms": 0.0,
            "context_assembly_ms": 0.0,
            "mcp_tool_call_ms": 0.0,
            "memory_usage_mb": 0.0,
            "cpu_idle_pct": 0.0,
            "last_reset": datetime.now(UTC).isoformat(),
        }

    def update_metrics(self, metric: str, value: Any) -> None:
        """Update a performance metric."""
        self.metrics[metric] = value

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status with performance metrics."""
        return {
            "metrics": self.metrics,
            "agent_count": len(self.agents),
            "task_count": len(self.tasks),
            "plan_count": len(self.plans),
        }

    def register_agent(self, agent: AgentStatus) -> None:
        """Register an agent."""
        self.agents[agent.agent_id] = agent
        self._notify("agent_registered", agent.agent_id)

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._notify("agent_unregistered", agent_id)
            return True
        return False

    def register_task(self, plan_id: str, task: Task) -> None:
        """Register a task for monitoring."""
        # Handle both Task (automation) and PlanTask (CLI planning)
        task_state = getattr(task, "state", getattr(task, "status", None))
        task_type = getattr(task, "task_type", None)
        task_priority = getattr(task, "priority", 0)
        if hasattr(task_priority, "value"):
            task_priority = task_priority.value

        monitor_data = TaskMonitorData(
            task_id=task.task_id,
            plan_id=UUID(plan_id),
            title=task.title,
            task_type=task_type,
            state=task_state,
            priority=task_priority,
            assigned_agent=getattr(task, "assigned_agent_id", None),
        )
        self.tasks[str(task.task_id)] = monitor_data
        self._notify("task_registered", str(task.task_id))

    def update_task(self, task: Task) -> None:
        """Update task monitoring data."""
        task_id = str(task.task_id)
        if task_id not in self.tasks:
            return

        monitor_data = self.tasks[task_id]
        task_state = getattr(task, "state", getattr(task, "status", None))
        monitor_data.state = task_state
        monitor_data.assigned_agent = getattr(task, "assigned_agent_id", None)

        # Calculate progress based on state
        state_progress: dict[TaskState, float] = {
            TaskState.CREATED: 0.0,
            TaskState.READY: 0.25,
            TaskState.RUNNING: 0.5,
            TaskState.COMPLETED: 1.0,
            TaskState.FAILED: 0.0,
            TaskState.CANCELLED: 0.0,
            TaskState.BLOCKED: 0.1,
        }
        monitor_data.progress = state_progress.get(task_state, 0.0)

        if monitor_data.started_at is None and task_state == TaskState.RUNNING:
            monitor_data.started_at = datetime.now(UTC)

        # Estimate completion time
        if monitor_data.started_at and monitor_data.retry_count > 0:
            monitor_data.estimated_completion = (
                datetime.now(UTC) + __import__("asyncio").get_event_loop().time() * 0  # placeholder
            )

        self._notify("task_updated", str(task.task_id))

    def clear_task(self, task_id: str) -> None:
        """Clear a task from monitoring."""
        self.tasks.pop(task_id, None)
        self._notify("task_cleared", task_id)

    def register_plan(self, plan: TaskPlan) -> None:
        """Register a plan for monitoring."""
        self.plans[str(plan.plan_id)] = plan
        self._notify("plan_registered", str(plan.plan_id))

    def unregister_plan(self, plan_id: str) -> bool:
        """Unregister a plan."""
        if plan_id in self.plans:
            del self.plans[plan_id]
            self._notify("plan_unregistered", plan_id)
            return True
        return False

    def add_quality_gate(self, result: QualityGateResult) -> None:
        """Add a quality gate result."""
        self.quality_gates.append(result)
        self._notify("quality_gate", result.gate_name)

    def clear_quality_gates(self) -> None:
        """Clear all quality gate results."""
        self.quality_gates.clear()

    def register_provider(
        self,
        provider: ProviderMonitorData,
    ) -> None:
        """Register a provider."""
        self.providers[provider.provider] = provider
        self._notify("provider_registered", provider.provider)

    def unregister_provider(self, provider_name: str) -> bool:
        """Unregister a provider."""
        if provider_name in self.providers:
            del self.providers[provider_name]
            self._notify("provider_unregistered", provider_name)
            return True
        return False

    def list_agents(self) -> list[AgentStatus]:
        """List all agents."""
        return list(self.agents.values())

    def list_tasks(self) -> list[TaskMonitorData]:
        """List all tasks."""
        return list(self.tasks.values())

    def list_plans(self) -> list[TaskPlan]:
        """List all plans."""
        return list(self.plans.values())

    def list_providers(self) -> list[ProviderMonitorData]:
        """List all providers."""
        return list(self.providers.values())

    def add_event_listener(self, listener: Callable[[str, Any], None]) -> None:
        """Add an event listener."""
        self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[str, Any], None]) -> bool:
        """Remove an event listener."""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
            return True
        return False

    def _notify(self, event_type: str, data: Any) -> None:
        """Notify event listeners."""
        for listener in self._event_listeners:
            try:
                listener(event_type, data)
            except Exception as exc:
                logger.warning("Event listener error: %s", exc)


# Global monitor instance
_global_monitor: OrchestrationMonitor | None = None


def get_monitor() -> OrchestrationMonitor:
    """Get the global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = OrchestrationMonitor()
    return _global_monitor
