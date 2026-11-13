"""Task executor for autonomous agent orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

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


class TaskExecutor:
    """Executes tasks with proper isolation, monitoring, and recovery."""

    def __init__(
        self,
        store: TaskStore | None = None,
        event_logger: TaskEventLogger | None = None,
        max_concurrent: int = 4,
        default_timeout: float = 300.0,
    ) -> None:
        self.store = store or TaskStore()
        self.event_logger = event_logger or TaskEventLogger()
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._running: dict[str, asyncio.Task[Any]] = {}
        self._cancelled: set[str] = set()
        self._semaphore: asyncio.Semaphore | None = None
        self._task_handlers: dict[TaskType, Callable[[Task, TaskPlan], Awaitable[TaskResult]]] = {}

    def register_handler(
        self, task_type: TaskType, handler: Callable[[Task, TaskPlan], Awaitable[TaskResult]]
    ) -> None:
        """Register a handler for a task type."""
        self._task_handlers[task_type] = handler

    async def start(self) -> None:
        """Start the executor."""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

    async def stop(self) -> None:
        """Stop the executor and cancel all running tasks."""
        for task_id, task in self._running.items():
            task.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        self._running.clear()

    async def execute_plan(self, plan: TaskPlan) -> TaskPlan:
        """Execute all tasks in a plan."""
        await self.start()

        try:
            while not plan.is_complete():
                # Get ready tasks
                completed = plan.get_completed_tasks()
                ready_tasks = plan.get_ready_tasks(completed)

                if not ready_tasks:
                    # Check if there are running tasks
                    running = plan.get_running_tasks()
                    if not running:
                        # No ready tasks and no running tasks - check for failures
                        failed = plan.get_failed_tasks()
                        if failed:
                            logger.warning("Plan %s has failed tasks, cannot proceed", plan.plan_id)
                            break
                        # Check for blocked tasks
                        blocked = [t for t in plan.tasks if t.state == TaskState.BLOCKED]
                        if blocked:
                            logger.warning("Plan %s has blocked tasks", plan.plan_id)
                            break
                        # Nothing to do
                        break

                    # Wait for running tasks
                    await self._wait_for_running(plan)
                    continue

                # Execute ready tasks (up to concurrency limit)
                running_count = len(plan.get_running_tasks())
                available_slots = self.max_concurrent - running_count

                if available_slots <= 0:
                    await self._wait_for_running(plan)
                    continue

                tasks_to_run = ready_tasks[:available_slots]

                for task in tasks_to_run:
                    await self._execute_task(plan, task)

            return plan

        finally:
            await self.stop()

    async def _wait_for_running(self, plan: TaskPlan) -> None:
        """Wait for at least one running task to complete."""
        running = plan.get_running_tasks()
        if not running:
            return

        # Wait for any running task
        tasks_to_wait = [
            self._running[str(t.task_id)] for t in running if str(t.task_id) in self._running
        ]
        if not tasks_to_wait:
            return

        done, _ = await asyncio.wait(
            tasks_to_wait,
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Update task states from results
        for fut in done:
            if fut.cancelled():
                task_id = None
                for tid, t in self._running.items():
                    if t is fut:
                        task_id = tid
                        break
                if task_id:
                    task = plan.get_task(UUID(task_id))
                    if task:
                        task.transition_to(TaskState.CANCELLED)
                        task.result = TaskResult(success=False, error="Task cancelled")
                        self.event_logger.log_event(
                            str(plan.plan_id), task_id, "cancelled", "Task cancelled"
                        )
                        self.store.update_task(str(plan.plan_id), task)

    async def _execute_task(self, plan: TaskPlan, task: Task) -> None:
        """Execute a single task."""
        task_id = str(task.task_id)
        plan_id = str(plan.plan_id)

        # Transition to running
        if not task.transition_to(TaskState.RUNNING):
            logger.warning("Cannot transition task %s to RUNNING from %s", task_id, task.state)
            return

        self.store.update_task(plan_id, task)
        self.event_logger.log_event(plan_id, task_id, "started", f"Task started: {task.title}")

        # Create asyncio task
        async_task = asyncio.create_task(self._run_task_with_timeout(plan, task))
        self._running[task_id] = async_task

        try:
            await async_task
        except asyncio.CancelledError:
            # Already handled in _wait_for_running
            pass
        except Exception as exc:
            logger.error("Task %s failed with exception: %s", task_id, exc)
            task.transition_to(TaskState.FAILED)
            task.result = TaskResult(success=False, error=str(exc))
            self.store.update_task(plan_id, task)
            self.event_logger.log_event(plan_id, task_id, "failed", f"Task failed: {exc}")
        finally:
            self._running.pop(task_id, None)

    async def _run_task_with_timeout(self, plan: TaskPlan, task: Task) -> None:
        """Run task with timeout."""
        task_id = str(task.task_id)
        plan_id = str(plan.plan_id)

        handler = self._task_handlers.get(task.task_type)
        if not handler:
            task.transition_to(TaskState.FAILED)
            task.result = TaskResult(
                success=False, error=f"No handler for task type: {task.task_type.value}"
            )
            self.store.update_task(plan_id, task)
            self.event_logger.log_event(plan_id, task_id, "failed", "No handler registered")
            return

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task, plan),
                timeout=task.timeout_seconds,
            )

            if result.success:
                task.transition_to(TaskState.COMPLETED)
            # Check if we should retry
            elif task.retry_count < task.max_retries:
                task.retry_count += 1
                task.transition_to(TaskState.REPAIRING)
                self.event_logger.log_event(
                    plan_id,
                    task_id,
                    "retry",
                    f"Task failed, retry {task.retry_count}/{task.max_retries}: {result.error}",
                )
                # Re-queue for retry
                task.transition_to(TaskState.READY)
            else:
                task.transition_to(TaskState.FAILED)

            task.result = result
            self.store.update_task(plan_id, task)

            if result.success:
                self.event_logger.log_event(
                    plan_id,
                    task_id,
                    "completed",
                    f"Task completed: {task.title}",
                    {"files_modified": result.files_modified},
                )
            elif task.state == TaskState.FAILED:
                self.event_logger.log_event(
                    plan_id, task_id, "failed", f"Task failed: {result.error}"
                )

        except TimeoutError:
            task.transition_to(TaskState.FAILED)
            task.result = TaskResult(
                success=False, error=f"Task timed out after {task.timeout_seconds}s"
            )
            self.store.update_task(plan_id, task)
            self.event_logger.log_event(plan_id, task_id, "timeout", "Task timed out")

        except Exception as exc:
            task.transition_to(TaskState.FAILED)
            task.result = TaskResult(success=False, error=f"Handler exception: {exc}")
            self.store.update_task(plan_id, task)
            self.event_logger.log_event(plan_id, task_id, "error", f"Handler exception: {exc}")


async def create_task_plan(
    objective: str,
    tasks: list[dict[str, Any]],
) -> TaskPlan:
    """Create a task plan from a list of task definitions."""
    plan = TaskPlan(objective=objective)

    for task_def in tasks:
        task = Task(
            task_type=TaskType(task_def.get("type", "implement")),
            title=task_def.get("title", ""),
            description=task_def.get("description", ""),
            priority=TaskPriority(task_def.get("priority", TaskPriority.NORMAL.value)),
            max_retries=task_def.get("max_retries", 3),
            timeout_seconds=task_def.get("timeout_seconds", 300.0),
            context=task_def.get("context", {}),
            file_ownership=task_def.get("file_ownership", []),
            tags=set(task_def.get("tags", [])),
        )

        # Add dependencies
        for dep_id in task_def.get("depends_on", []):
            task.add_dependency(UUID(dep_id))

        plan.add_task(task)

    return plan
