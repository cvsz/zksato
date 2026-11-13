"""Plan mode for ZKSATO coding agent.

Implements the full plan lifecycle:
DISCOVER → ANALYZE → PLAN → APPROVE → EXECUTE → REVIEW → VERIFY → COMPLETE

Features:
- Read-only exploration mode
- Explicit implementation plans
- Dependency graphs
- Task prioritization
- Plan revision
- User approval gates
- Progress tracking
- Partial execution recovery
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from zksato_cli.sessions.persistence import SessionManager

logger = logging.getLogger(__name__)


class PlanPhase(str, Enum):
    """Plan execution phases."""

    DISCOVER = "discover"
    ANALYZE = "analyze"
    PLAN = "plan"
    APPROVE = "approve"
    EXECUTE = "execute"
    REVIEW = "review"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    """Types of tasks in a plan."""

    EXPLORATION = "exploration"  # Read-only code exploration
    ANALYSIS = "analysis"  # Code analysis, understanding
    FILE_READ = "file_read"  # Read files
    FILE_WRITE = "file_write"  # Write new files
    FILE_MODIFY = "file_modify"  # Modify existing files
    FILE_DELETE = "file_delete"  # Delete files
    COMMAND = "command"  # Run shell commands
    TEST = "test"  # Run tests
    LINT = "lint"  # Run linters
    REVIEW = "review"  # Code review
    DOCUMENTATION = "documentation"  # Update docs


class ApprovalStatus(str, Enum):
    """Approval gate status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass
class PlanTask:
    """A single task in a plan."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.ANALYSIS
    title: str = ""
    description: str = ""
    phase: PlanPhase = PlanPhase.PLAN

    # Execution
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0  # Higher = more important
    dependencies: list[str] = field(default_factory=list)  # Task IDs

    # Parameters
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""

    # Results
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Approval
    requires_approval: bool = False
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approval_reason: str = ""

    # Retry
    retry_count: int = 0
    max_retries: int = 3

    def can_run(self, completed_tasks: set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep in completed_tasks for dep in self.dependencies)

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "title": self.title,
            "description": self.description,
            "phase": self.phase.value,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "parameters": self.parameters,
            "expected_output": self.expected_output,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status.value,
            "approval_reason": self.approval_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanTask:
        """Deserialize task from dictionary."""
        task = cls(
            task_id=data["task_id"],
            task_type=TaskType(data["task_type"]),
            title=data["title"],
            description=data["description"],
            phase=PlanPhase(data["phase"]),
            status=TaskStatus(data["status"]),
            priority=data.get("priority", 0),
            dependencies=data.get("dependencies", []),
            parameters=data.get("parameters", {}),
            expected_output=data.get("expected_output", ""),
            requires_approval=data.get("requires_approval", False),
            approval_status=ApprovalStatus(data.get("approval_status", "pending")),
            approval_reason=data.get("approval_reason", ""),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        return task


@dataclass
class ApprovalGate:
    """An approval gate in the plan."""

    gate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    phase: PlanPhase = PlanPhase.APPROVE

    # Gate criteria
    required_approvers: int = 1
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    approvers: list[str] = field(default_factory=list)
    decided_at: datetime | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase.value,
            "required_approvers": self.required_approvers,
            "auto_approve_conditions": self.auto_approve_conditions,
            "status": self.status.value,
            "approvers": self.approvers,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalGate:
        gate = cls(
            gate_id=data["gate_id"],
            name=data["name"],
            description=data["description"],
            phase=PlanPhase(data["phase"]),
            required_approvers=data.get("required_approvers", 1),
            auto_approve_conditions=data.get("auto_approve_conditions", {}),
            status=ApprovalStatus(data.get("status", "pending")),
            approvers=data.get("approvers", []),
            reason=data.get("reason", ""),
        )
        if data.get("decided_at"):
            gate.decided_at = datetime.fromisoformat(data["decided_at"])
        return gate


@dataclass
class Plan:
    """A complete execution plan."""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    objective: str = ""
    title: str = ""

    # Plan structure
    tasks: list[PlanTask] = field(default_factory=list)
    approval_gates: list[ApprovalGate] = field(default_factory=list)

    # State
    current_phase: PlanPhase = PlanPhase.DISCOVER
    status: PlanPhase = PlanPhase.DISCOVER

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Exploration mode
    read_only_mode: bool = True  # Start in read-only exploration

    def add_task(self, task: PlanTask) -> None:
        """Add a task to the plan."""
        self.tasks.append(task)
        self.updated_at = datetime.now(UTC)

    def add_approval_gate(self, gate: ApprovalGate) -> None:
        """Add an approval gate."""
        self.approval_gates.append(gate)
        self.updated_at = datetime.now(UTC)

    def get_task(self, task_id: str) -> PlanTask | None:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_ready_tasks(self, completed_tasks: set[str]) -> list[PlanTask]:
        """Get tasks that are ready to run."""
        ready = []
        ready = [
            task
            for task in self.tasks
            if task.status == TaskStatus.PENDING and task.can_run(completed_tasks)
        ]
        # Sort by priority (highest first)
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    def get_tasks_by_phase(self, phase: PlanPhase) -> list[PlanTask]:
        """Get all tasks in a specific phase."""
        return [t for t in self.tasks if t.phase == phase]

    def get_completed_tasks(self) -> set[str]:
        """Get set of completed task IDs."""
        return {t.task_id for t in self.tasks if t.status == TaskStatus.COMPLETED}

    def get_failed_tasks(self) -> list[PlanTask]:
        """Get failed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]

    def get_pending_approvals(self) -> list[PlanTask]:
        """Get tasks pending approval."""
        return [
            t
            for t in self.tasks
            if t.requires_approval and t.approval_status == ApprovalStatus.PENDING
        ]

    def get_approval_gate(self, phase: PlanPhase) -> ApprovalGate | None:
        """Get approval gate for a phase."""
        for gate in self.approval_gates:
            if gate.phase == phase:
                return gate
        return None

    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        return all(t.is_terminal() for t in self.tasks)

    def has_failures(self) -> bool:
        """Check if any tasks failed."""
        return any(t.status == TaskStatus.FAILED for t in self.tasks)

    def progress(self) -> float:
        """Get completion progress (0.0 to 1.0)."""
        if not self.tasks:
            return 1.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize plan to dictionary."""
        return {
            "plan_id": self.plan_id,
            "session_id": self.session_id,
            "objective": self.objective,
            "title": self.title,
            "tasks": [t.to_dict() for t in self.tasks],
            "approval_gates": [g.to_dict() for g in self.approval_gates],
            "current_phase": self.current_phase.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "read_only_mode": self.read_only_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        """Deserialize plan from dictionary."""
        plan = cls(
            plan_id=data["plan_id"],
            session_id=data.get("session_id", ""),
            objective=data["objective"],
            title=data.get("title", ""),
            current_phase=PlanPhase(data.get("current_phase", "discover")),
            status=PlanPhase(data.get("status", "discover")),
            metadata=data.get("metadata", {}),
            read_only_mode=data.get("read_only_mode", True),
        )

        if data.get("created_at"):
            plan.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            plan.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("started_at"):
            plan.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            plan.completed_at = datetime.fromisoformat(data["completed_at"])

        for task_data in data.get("tasks", []):
            plan.tasks.append(PlanTask.from_dict(task_data))

        for gate_data in data.get("approval_gates", []):
            plan.approval_gates.append(ApprovalGate.from_dict(gate_data))

        return plan


class PlanStore:
    """Persistent plan storage."""

    def __init__(self, storage_dir: Path | str = ".zksato/plans") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self._index_file.exists():
            try:
                with self._index_file.open("r") as f:
                    self._index = json.load(f)
            except Exception as exc:
                logger.warning("Failed to load plan index: %s", exc)
                self._index = {}

    def _save_index(self) -> None:
        try:
            with self._index_file.open("w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save plan index: %s", exc)

    def _get_plan_file(self, plan_id: str) -> Path:
        return self.storage_dir / f"{plan_id}.json"

    def save_plan(self, plan: Plan) -> None:
        """Save plan to disk."""
        plan.updated_at = datetime.now(UTC)
        plan_file = self._get_plan_file(plan.plan_id)

        try:
            with plan_file.open("w") as f:
                json.dump(plan.to_dict(), f, indent=2)

            self._index[plan.plan_id] = {
                "plan_id": plan.plan_id,
                "session_id": plan.session_id,
                "title": plan.title,
                "objective": plan.objective[:100],
                "status": plan.status.value,
                "current_phase": plan.current_phase.value,
                "progress": plan.progress(),
                "task_count": len(plan.tasks),
                "completed_tasks": sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED),
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat(),
            }
            self._save_index()
        except Exception as exc:
            logger.error("Failed to save plan %s: %s", plan.plan_id, exc)
            raise

    def load_plan(self, plan_id: str) -> Plan | None:
        """Load plan from disk."""
        plan_file = self._get_plan_file(plan_id)
        if not plan_file.exists():
            return None

        try:
            with plan_file.open("r") as f:
                data = json.load(f)
            return Plan.from_dict(data)
        except Exception as exc:
            logger.error("Failed to load plan %s: %s", plan_id, exc)
            return None

    def delete_plan(self, plan_id: str) -> bool:
        plan_file = self._get_plan_file(plan_id)
        if plan_file.exists():
            plan_file.unlink()
        if plan_id in self._index:
            del self._index[plan_id]
            self._save_index()
            return True
        return False

    def list_plans(
        self,
        session_id: str | None = None,
        status: PlanPhase | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        plans = list(self._index.values())
        if session_id:
            plans = [p for p in plans if p.get("session_id") == session_id]
        if status:
            plans = [p for p in plans if p.get("status") == status.value]
        plans.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return plans[:limit]


class PlanExecutor:
    """Executes a plan with approval gates and progress tracking."""

    def __init__(
        self,
        plan: Plan,
        session_manager: SessionManager,
        project_root: Path,
        approval_callback: callable | None = None,
    ) -> None:
        self.plan = plan
        self.session_manager = session_manager
        self.project_root = Path(project_root).resolve()
        self.approval_callback = approval_callback
        self._running = False

    async def execute(self) -> Plan:
        """Execute the plan."""
        self._running = True
        self.plan.status = PlanPhase.EXECUTE
        self.plan.started_at = datetime.now(UTC)

        try:
            # Execute phases in order
            phases = [
                PlanPhase.DISCOVER,
                PlanPhase.ANALYZE,
                PlanPhase.PLAN,
                PlanPhase.APPROVE,
                PlanPhase.EXECUTE,
                PlanPhase.REVIEW,
                PlanPhase.VERIFY,
                PlanPhase.COMPLETE,
            ]

            for phase in phases:
                if not self._running:
                    break

                self.plan.current_phase = phase
                await self._execute_phase(phase)

                # Check for failures
                if self.plan.has_failures():
                    self.plan.status = PlanPhase.FAILED
                    break

            if self.plan.status != PlanPhase.FAILED:
                self.plan.status = PlanPhase.COMPLETE

        finally:
            self.plan.completed_at = datetime.now(UTC)
            self._running = False

        return self.plan

    async def _execute_phase(self, phase: PlanPhase) -> None:
        """Execute all tasks in a phase."""
        # Check approval gate
        gate = self.plan.get_approval_gate(phase)
        if gate and gate.status == ApprovalStatus.PENDING:
            await self._request_approval(gate)
            if gate.status != ApprovalStatus.APPROVED:
                # Mark phase tasks as skipped
                for task in self.plan.get_tasks_by_phase(phase):
                    task.status = TaskStatus.SKIPPED
                return

        # Get tasks for this phase
        tasks = self.plan.get_tasks_by_phase(phase)
        completed = self.plan.get_completed_tasks()

        # Execute ready tasks
        while True:
            ready = [t for t in tasks if t.status == TaskStatus.PENDING and t.can_run(completed)]
            if not ready:
                break

            # Run tasks (could be parallelized)
            for task in ready:
                if not self._running:
                    return
                await self._execute_task(task)
                completed = self.plan.get_completed_tasks()

    async def _execute_task(self, task: PlanTask) -> None:
        """Execute a single task."""
        # Check approval
        if task.requires_approval and task.approval_status == ApprovalStatus.PENDING:
            if self.approval_callback:
                approved = await self.approval_callback(task)
                if not approved:
                    task.approval_status = ApprovalStatus.REJECTED
                    task.status = TaskStatus.SKIPPED
                    return
            else:
                task.approval_status = ApprovalStatus.PENDING
                return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)

        try:
            # Execute based on task type
            result = await self._run_task_action(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
        except Exception as exc:
            task.error = str(exc)
            task.status = TaskStatus.FAILED
            logger.error("Task %s failed: %s", task.task_id, exc)

        task.completed_at = datetime.now(UTC)

    async def _run_task_action(self, task: PlanTask) -> Any:
        """Run the actual task action based on type."""
        params = task.parameters

        if task.task_type == TaskType.EXPLORATION:
            # Read-only exploration
            return await self._explore(params)

        elif task.task_type == TaskType.FILE_READ:
            return await self._read_file(params)

        elif task.task_type == TaskType.FILE_WRITE:
            if self.plan.read_only_mode:
                raise PermissionError("Cannot write in read-only mode")
            return await self._write_file(params)

        elif task.task_type == TaskType.FILE_MODIFY:
            if self.plan.read_only_mode:
                raise PermissionError("Cannot modify in read-only mode")
            return await self._modify_file(params)

        elif task.task_type == TaskType.FILE_DELETE:
            if self.plan.read_only_mode:
                raise PermissionError("Cannot delete in read-only mode")
            return await self._delete_file(params)

        elif task.task_type == TaskType.COMMAND:
            return await self._run_command(params)

        elif task.task_type == TaskType.TEST:
            return await self._run_tests(params)

        elif task.task_type == TaskType.LINT:
            return await self._run_lint(params)

        elif task.task_type == TaskType.ANALYSIS:
            return await self._analyze(params)

        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

    async def _explore(self, params: dict[str, Any]) -> dict[str, Any]:
        """Read-only code exploration."""
        # This would use the search/edit tools
        return {"explored": True, "files": params.get("files", [])}

    async def _read_file(self, params: dict[str, Any]) -> str:
        """Read a file."""
        file_path = self.project_root / params["path"]
        return file_path.read_text(encoding="utf-8")

    async def _write_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Write a file."""
        file_path = self.project_root / params["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(params["content"], encoding="utf-8")
        return {"written": True, "path": params["path"]}

    async def _modify_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Modify a file."""
        # This would use the patch engine
        return {"modified": True, "path": params["path"]}

    async def _delete_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete a file."""
        file_path = self.project_root / params["path"]
        file_path.unlink()
        return {"deleted": True, "path": params["path"]}

    async def _run_command(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a shell command."""
        import shlex
        import subprocess

        cmd = params["command"]
        cwd = params.get("cwd", str(self.project_root))
        cmd_list = shlex.split(cmd)
        proc = subprocess.run(
            cmd_list,
            shell=False,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=params.get("timeout", 60),
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }

    async def _run_tests(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run tests."""
        import shlex
        import subprocess

        cmd = params.get("command", "python -m pytest")
        cmd_list = shlex.split(cmd)
        proc = subprocess.run(
            cmd_list,
            shell=False,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
            timeout=params.get("timeout", 120),
        )
        return {
            "passed": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    async def _run_lint(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run linter."""
        import shlex
        import subprocess

        cmd = params.get("command", "ruff check .")
        cmd_list = shlex.split(cmd)
        proc = subprocess.run(
            cmd_list,
            shell=False,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        return {
            "passed": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    async def _analyze(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze code."""
        return {"analyzed": True}

    async def _request_approval(self, gate: ApprovalGate) -> None:
        """Request approval for a gate."""
        if self.approval_callback:
            approved = await self.approval_callback(gate)
            gate.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            gate.decided_at = datetime.now(UTC)
        else:
            # Auto-approve if no callback
            gate.status = ApprovalStatus.APPROVED
            gate.decided_at = datetime.now(UTC)


class PlanBuilder:
    """Builds plans from objectives."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()

    def create_exploration_plan(
        self,
        objective: str,
        session_id: str,
        files_to_explore: list[str] | None = None,
    ) -> Plan:
        """Create a read-only exploration plan."""
        plan = Plan(
            session_id=session_id,
            objective=objective,
            title=f"Explore: {objective[:50]}",
            read_only_mode=True,
        )

        # Discovery phase
        plan.add_task(
            PlanTask(
                task_type=TaskType.EXPLORATION,
                title="Explore codebase structure",
                description="Get overview of project structure and key files",
                phase=PlanPhase.DISCOVER,
                priority=100,
                parameters={"files": files_to_explore or []},
            )
        )

        # Analysis phase
        plan.add_task(
            PlanTask(
                task_type=TaskType.ANALYSIS,
                title="Analyze relevant code",
                description="Deep dive into relevant modules",
                phase=PlanPhase.ANALYZE,
                priority=90,
                dependencies=[],  # Will be filled after discovery
            )
        )

        return plan

    def create_implementation_plan(
        self,
        objective: str,
        session_id: str,
        exploration_findings: dict[str, Any],
    ) -> Plan:
        """Create an implementation plan based on exploration."""
        plan = Plan(
            session_id=session_id,
            objective=objective,
            title=f"Implement: {objective[:50]}",
            read_only_mode=False,
        )

        # Plan phase
        plan.add_task(
            PlanTask(
                task_type=TaskType.ANALYSIS,
                title="Create implementation plan",
                description="Design the implementation approach",
                phase=PlanPhase.PLAN,
                priority=100,
            )
        )

        # Approval gate
        plan.add_approval_gate(
            ApprovalGate(
                name="Implementation Plan Review",
                description="Review and approve the implementation plan",
                phase=PlanPhase.APPROVE,
                required_approvers=1,
            )
        )

        # Execute phase - tasks would be added based on plan
        plan.add_task(
            PlanTask(
                task_type=TaskType.FILE_WRITE,
                title="Implement core changes",
                description="Write new implementation files",
                phase=PlanPhase.EXECUTE,
                priority=80,
                requires_approval=True,
            )
        )

        # Test phase
        plan.add_task(
            PlanTask(
                task_type=TaskType.TEST,
                title="Run tests",
                description="Execute test suite",
                phase=PlanPhase.VERIFY,
                priority=70,
            )
        )

        # Review phase
        plan.add_task(
            PlanTask(
                task_type=TaskType.REVIEW,
                title="Code review",
                description="Review implementation",
                phase=PlanPhase.REVIEW,
                priority=60,
            )
        )

        return plan


class PlanManager:
    """High-level plan management."""

    def __init__(
        self,
        project_root: Path,
        session_manager: SessionManager,
        storage_dir: Path | str = ".zksato/plans",
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.session_manager = session_manager
        self.store = PlanStore(storage_dir)
        self.builder = PlanBuilder(project_root)
        self._current_plan: Plan | None = None

    def create_plan(self, plan: Plan) -> Plan:
        """Create and save a new plan."""
        self.store.save_plan(plan)
        self._current_plan = plan
        return plan

    def load_plan(self, plan_id: str) -> Plan | None:
        plan = self.store.load_plan(plan_id)
        if plan:
            self._current_plan = plan
        return plan

    def get_current_plan(self) -> Plan | None:
        return self._current_plan

    def list_plans(
        self,
        session_id: str | None = None,
        status: PlanPhase | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.store.list_plans(session_id, status, limit)

    def delete_plan(self, plan_id: str) -> bool:
        if self._current_plan and self._current_plan.plan_id == plan_id:
            self._current_plan = None
        return self.store.delete_plan(plan_id)

    async def execute_plan(
        self,
        plan: Plan,
        approval_callback: callable | None = None,
    ) -> Plan:
        """Execute a plan."""
        executor = PlanExecutor(plan, self.session_manager, self.project_root, approval_callback)
        return await executor.execute()

    def create_exploration_plan(
        self,
        objective: str,
        session_id: str,
        files_to_explore: list[str] | None = None,
    ) -> Plan:
        """Create an exploration plan."""
        plan = self.builder.create_exploration_plan(objective, session_id, files_to_explore)
        return self.create_plan(plan)

    def create_implementation_plan(
        self,
        objective: str,
        session_id: str,
        exploration_findings: dict[str, Any],
    ) -> Plan:
        """Create an implementation plan."""
        plan = self.builder.create_implementation_plan(objective, session_id, exploration_findings)
        return self.create_plan(plan)
