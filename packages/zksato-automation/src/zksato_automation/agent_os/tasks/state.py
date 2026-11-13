"""Task state management for autonomous agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from zksato_core.ids import new_uuid  # type: ignore[import-untyped]


class TaskState(str, Enum):
    """Task lifecycle states."""

    CREATED = "created"
    ANALYZING = "analyzing"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    REVIEWING = "reviewing"
    TESTING = "testing"
    REPAIRING = "repairing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


class TaskType(str, Enum):
    """Types of tasks."""

    DISCOVER = "discover"
    ANALYZE = "analyze"
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    TEST = "test"
    REPAIR = "repair"
    FINALIZE = "finalize"
    SECURITY_AUDIT = "security_audit"
    ARCHITECTURE_REVIEW = "architecture_review"
    DOCUMENTATION = "documentation"


# Valid state transitions
VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.CREATED: {TaskState.ANALYZING, TaskState.READY, TaskState.CANCELLED},
    TaskState.ANALYZING: {TaskState.PLANNED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.PLANNED: {TaskState.READY, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.READY: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.REVIEWING,
        TaskState.TESTING,
        TaskState.REPAIRING,
        TaskState.BLOCKED,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.REVIEWING: {
        TaskState.TESTING,
        TaskState.REPAIRING,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.TESTING: {
        TaskState.COMPLETED,
        TaskState.REPAIRING,
        TaskState.FAILED,
        TaskState.CANCELLED,
    },
    TaskState.REPAIRING: {TaskState.TESTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.BLOCKED: {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.COMPLETED: set(),  # Terminal
    TaskState.FAILED: {TaskState.REPAIRING, TaskState.CANCELLED},
    TaskState.CANCELLED: set(),  # Terminal
}


@dataclass
class TaskDependency:
    """Task dependency."""

    task_id: UUID
    dependency_type: str = "blocks"  # blocks, requires, relates_to


@dataclass
class TaskResult:
    """Task execution result."""

    success: bool
    output: Any = None
    error: str | None = None
    files_modified: list[str] = field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    review_findings: list[dict[str, Any]] = field(default_factory=list)
    security_findings: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Autonomous agent task with persistent state."""

    task_id: UUID = field(default_factory=new_uuid)
    parent_task_id: UUID | None = None
    task_type: TaskType = TaskType.IMPLEMENT
    title: str = ""
    description: str = ""
    state: TaskState = TaskState.CREATED
    priority: TaskPriority = TaskPriority.NORMAL

    # Assignment
    assigned_agent_id: str | None = None
    assigned_agent_role: str | None = None

    # Dependencies
    dependencies: list[TaskDependency] = field(default_factory=list)

    # Execution
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Results
    result: TaskResult | None = None

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    file_ownership: list[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: set[str] = field(default_factory=set)

    def can_transition(self, new_state: TaskState) -> bool:
        """Check if state transition is valid."""
        return new_state in VALID_TRANSITIONS.get(self.state, set())

    def transition_to(self, new_state: TaskState) -> bool:
        """Transition to new state if valid."""
        if not self.can_transition(new_state):
            return False
        self.state = new_state
        self.updated_at = datetime.now(UTC)
        if new_state == TaskState.RUNNING and self.started_at is None:
            self.started_at = datetime.now(UTC)
        if new_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            self.completed_at = datetime.now(UTC)
        return True

    def add_dependency(self, task_id: UUID, dependency_type: str = "blocks") -> None:
        """Add a task dependency."""
        self.dependencies.append(TaskDependency(task_id=task_id, dependency_type=dependency_type))

    def is_ready(self, completed_tasks: set[UUID]) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in self.dependencies:
            if dep.dependency_type == "blocks" and dep.task_id not in completed_tasks:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "task_id": str(self.task_id),
            "parent_task_id": str(self.parent_task_id) if self.parent_task_id else None,
            "task_type": self.task_type.value,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "priority": self.priority.value,
            "assigned_agent_id": self.assigned_agent_id,
            "assigned_agent_role": self.assigned_agent_role,
            "dependencies": [
                {"task_id": str(d.task_id), "type": d.dependency_type} for d in self.dependencies
            ],
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": {
                "success": self.result.success if self.result else None,
                "error": self.result.error if self.result else None,
                "files_modified": self.result.files_modified if self.result else [],
                "tests_passed": self.result.tests_passed if self.result else 0,
                "tests_failed": self.result.tests_failed if self.result else 0,
            }
            if self.result
            else None,
            "context": self.context,
            "file_ownership": self.file_ownership,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Deserialize task from dictionary."""
        task = cls(
            task_id=UUID(data["task_id"]),
            parent_task_id=UUID(data["parent_task_id"]) if data.get("parent_task_id") else None,
            task_type=TaskType(data["task_type"]),
            title=data["title"],
            description=data["description"],
            state=TaskState(data["state"]),
            priority=TaskPriority(data["priority"]),
            assigned_agent_id=data.get("assigned_agent_id"),
            assigned_agent_role=data.get("assigned_agent_role"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 300.0),
            context=data.get("context", {}),
            file_ownership=data.get("file_ownership", []),
            tags=set(data.get("tags", [])),
        )

        # Parse dependencies
        for dep_data in data.get("dependencies", []):
            task.add_dependency(UUID(dep_data["task_id"]), dep_data.get("type", "blocks"))

        # Parse timestamps
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            task.updated_at = datetime.fromisoformat(data["updated_at"])

        # Parse result
        if data.get("result"):
            task.result = TaskResult(
                success=data["result"]["success"],
                error=data["result"]["error"],
                files_modified=data["result"].get("files_modified", []),
                tests_passed=data["result"].get("tests_passed", 0),
                tests_failed=data["result"].get("tests_failed", 0),
            )

        return task


@dataclass
class TaskPlan:
    """Collection of tasks forming a plan."""

    plan_id: UUID = field(default_factory=new_uuid)
    objective: str = ""
    tasks: list[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_task(self, task: Task) -> None:
        """Add task to plan."""
        self.tasks.append(task)
        self.updated_at = datetime.now(UTC)

    def get_task(self, task_id: UUID) -> Task | None:
        """Get task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_ready_tasks(self, completed_tasks: set[UUID]) -> list[Task]:
        """Get tasks that are ready to run."""
        ready = []
        for task in self.tasks:
            if task.state == TaskState.READY and task.is_ready(completed_tasks):
                ready.append(task)
        # Sort by priority (highest first)
        ready.sort(key=lambda t: t.priority.value, reverse=True)
        return ready

    def get_running_tasks(self) -> list[Task]:
        """Get currently running tasks."""
        return [t for t in self.tasks if t.state == TaskState.RUNNING]

    def get_completed_tasks(self) -> set[UUID]:
        """Get set of completed task IDs."""
        return {t.task_id for t in self.tasks if t.state == TaskState.COMPLETED}

    def get_failed_tasks(self) -> list[Task]:
        """Get failed tasks."""
        return [t for t in self.tasks if t.state == TaskState.FAILED]

    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(t.state in (TaskState.COMPLETED, TaskState.CANCELLED) for t in self.tasks)

    def has_failures(self) -> bool:
        """Check if any tasks failed."""
        return any(t.state == TaskState.FAILED for t in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize plan to dictionary."""
        return {
            "plan_id": str(self.plan_id),
            "objective": self.objective,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskPlan:
        """Deserialize plan from dictionary."""
        plan = cls(
            plan_id=UUID(data["plan_id"]),
            objective=data["objective"],
        )
        for task_data in data.get("tasks", []):
            task = Task.from_dict(task_data)
            plan.tasks.append(task)
        if data.get("created_at"):
            plan.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            plan.updated_at = datetime.fromisoformat(data["updated_at"])
        return plan
