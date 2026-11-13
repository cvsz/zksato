"""Task persistence for autonomous agent orchestration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from zksato_automation.agent_os.tasks.state import Task, TaskPlan, TaskState

logger = logging.getLogger(__name__)


class TaskStore:
    """Persistent task storage using JSON files."""

    def __init__(self, storage_dir: Path | str = ".zksato/tasks") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._plans: dict[str, TaskPlan] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all plans from storage."""
        for plan_file in self.storage_dir.glob("*.json"):
            try:
                with plan_file.open("r") as f:
                    data = json.load(f)
                plan = TaskPlan.from_dict(data)
                self._plans[str(plan.plan_id)] = plan
            except Exception as exc:
                logger.warning("Failed to load plan from %s: %s", plan_file, exc)

    def save_plan(self, plan: TaskPlan) -> None:
        """Save plan to storage."""
        plan_file = self.storage_dir / f"{plan.plan_id}.json"
        try:
            with plan_file.open("w") as f:
                json.dump(plan.to_dict(), f, indent=2)
            self._plans[str(plan.plan_id)] = plan
        except Exception as exc:
            logger.error("Failed to save plan %s: %s", plan.plan_id, exc)
            raise

    def get_plan(self, plan_id: str) -> TaskPlan | None:
        """Get plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> list[TaskPlan]:
        """List all plans."""
        return list(self._plans.values())

    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan."""
        plan_file = self.storage_dir / f"{plan_id}.json"
        if plan_file.exists():
            plan_file.unlink()
        return self._plans.pop(plan_id, None) is not None

    def get_task(self, plan_id: str, task_id: str) -> Task | None:
        """Get task from a plan."""
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        return plan.get_task(UUID(task_id))

    def update_task(self, plan_id: str, task: Task) -> bool:
        """Update a task in a plan."""
        plan = self.get_plan(plan_id)
        if not plan:
            return False
        # Find and replace task
        for i, t in enumerate(plan.tasks):
            if t.task_id == task.task_id:
                plan.tasks[i] = task
                self.save_plan(plan)
                return True
        return False

    def get_tasks_by_state(self, plan_id: str, state: TaskState) -> list[Task]:
        """Get all tasks in a plan with a specific state."""
        plan = self.get_plan(plan_id)
        if not plan:
            return []
        return [t for t in plan.tasks if t.state == state]


class TaskEventLogger:
    """Log task execution events for audit trail."""

    def __init__(self, log_dir: Path | str = ".zksato/tasks/events") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        plan_id: str,
        task_id: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log an event."""
        from datetime import UTC, datetime
        from uuid import uuid4

        event = {
            "event_id": str(uuid4()),
            "plan_id": plan_id,
            "task_id": task_id,
            "event_type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        log_file = self.log_dir / f"{plan_id}.jsonl"
        try:
            with log_file.open("a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as exc:
            logger.error("Failed to log event: %s", exc)

    def get_events(self, plan_id: str) -> list[dict[str, Any]]:
        """Get all events for a plan."""
        log_file = self.log_dir / f"{plan_id}.jsonl"
        if not log_file.exists():
            return []

        events = []
        try:
            with log_file.open("r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as exc:
            logger.error("Failed to read events: %s", exc)
        return events
