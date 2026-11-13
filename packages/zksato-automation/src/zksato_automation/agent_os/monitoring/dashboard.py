"""Real-time monitoring and dashboard for agent orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
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
    """Real-time orchestration monitor."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentStatus] = {}
        self.tasks: dict[str, TaskMonitorData] = {}
        self.plans: dict[str, TaskPlan] = {}
        self.providers: dict[str, ProviderMonitorData] = {}
        self.quality_gates: list[QualityGateResult] = []
        self._event_listeners: list[Callable[[str, Any], None]] = []
        self._lock = asyncio.Lock()

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

    def update_agent_status(self, agent_id: str, **kwargs: Any) -> bool:
        """Update agent status."""
        if agent_id not in self.agents:
            return False
        agent = self.agents[agent_id]
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        agent.last_activity = datetime.now(UTC)
        self._notify("agent_updated", agent_id)
        return True

    def get_agent(self, agent_id: str) -> AgentStatus | None:
        """Get agent status."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[AgentStatus]:
        """List all agents."""
        return list(self.agents.values())

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
        state_progress = {
            TaskState.CREATED: 0.0,
            TaskState.ANALYZING: 0.1,
            TaskState.PLANNED: 0.2,
            TaskState.READY: 0.3,
            TaskState.RUNNING: 0.5,
            TaskState.REVIEWING: 0.7,
            TaskState.TESTING: 0.85,
            TaskState.REPAIRING: 0.6,
            TaskState.BLOCKED: 0.4,
            TaskState.COMPLETED: 1.0,
            TaskState.FAILED: 0.0,
            TaskState.CANCELLED: 0.0,
        }
        # Handle both TaskState (automation) and TaskStatus (CLI planning)
        if task_state is not None:
            state_key = task_state.value if hasattr(task_state, "value") else task_state
            monitor_data.progress = state_progress.get(state_key, 0.0)

        monitor_data.retry_count = getattr(task, "retry_count", 0)

        if task.state == TaskState.RUNNING and not monitor_data.started_at:
            monitor_data.started_at = task.started_at

        self._notify("task_updated", task_id)

    def get_task(self, task_id: str) -> TaskMonitorData | None:
        """Get task monitoring data."""
        return self.tasks.get(task_id)

    def list_tasks(self, plan_id: str | None = None) -> list[TaskMonitorData]:
        """List tasks, optionally filtered by plan."""
        if plan_id:
            return [t for t in self.tasks.values() if str(t.plan_id) == plan_id]
        return list(self.tasks.values())

    def register_plan(self, plan: TaskPlan) -> None:
        """Register a plan."""
        self.plans[str(plan.plan_id)] = plan
        self._notify("plan_registered", str(plan.plan_id))

    def get_plan(self, plan_id: str) -> TaskPlan | None:
        """Get a plan."""
        return self.plans.get(plan_id)

    def list_plans(self) -> list[TaskPlan]:
        """List all plans."""
        return list(self.plans.values())

    def update_provider(self, data: ProviderMonitorData) -> None:
        """Update provider monitoring data."""
        self.providers[data.provider] = data
        self._notify("provider_updated", data.provider)

    def get_provider(self, provider: str) -> ProviderMonitorData | None:
        """Get provider monitoring data."""
        return self.providers.get(provider)

    def list_providers(self) -> list[ProviderMonitorData]:
        """List all providers."""
        return list(self.providers.values())

    def record_quality_gate(self, result: QualityGateResult) -> None:
        """Record a quality gate result."""
        self.quality_gates.append(result)
        self._notify("quality_gate", result.gate_name)

    def get_quality_gates(self, task_id: str | None = None) -> list[QualityGateResult]:
        """Get quality gate results."""
        if task_id:
            return [g for g in self.quality_gates if g.metrics.get("task_id") == task_id]
        return list(self.quality_gates)

    def get_overview(self) -> dict[str, Any]:
        """Get overview statistics."""
        agent_statuses: defaultdict[str, int] = defaultdict(int)
        for agent in self.agents.values():
            agent_statuses[agent.status] += 1

        task_states: defaultdict[str, int] = defaultdict(int)
        for task in self.tasks.values():
            task_states[task.state.value] += 1

        provider_statuses: defaultdict[str, int] = defaultdict(int)
        for provider in self.providers.values():
            provider_statuses[provider.status] += 1

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "agents": {
                "total": len(self.agents),
                "by_status": dict(agent_statuses),
            },
            "tasks": {
                "total": len(self.tasks),
                "by_state": dict(task_states),
            },
            "plans": {
                "total": len(self.plans),
                "active": sum(1 for p in self.plans.values() if not p.is_complete()),
            },
            "providers": {
                "total": len(self.providers),
                "by_status": dict(provider_statuses),
            },
            "quality_gates": {
                "total": len(self.quality_gates),
                "passed": sum(1 for g in self.quality_gates if g.passed),
                "failed": sum(1 for g in self.quality_gates if not g.passed),
            },
        }

    def get_task_hierarchy(self, plan_id: str) -> dict[str, Any] | None:
        """Get task hierarchy for a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None

        return {
            "plan_id": plan_id,
            "objective": plan.objective,
            "tasks": [
                {
                    "task_id": str(t.task_id),
                    "title": t.title,
                    "type": t.task_type.value,
                    "state": t.state.value,
                    "priority": t.priority.value,
                    "dependencies": [str(d.task_id) for d in t.dependencies],
                    "progress": self.tasks.get(
                        str(t.task_id),
                        TaskMonitorData(
                            task_id=t.task_id,
                            plan_id=plan.plan_id,
                            title=t.title,
                            task_type=t.task_type,
                            state=t.state,
                            priority=t.priority.value,
                            assigned_agent=None,
                        ),
                    ).progress,
                }
                for t in plan.tasks
            ],
        }

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
