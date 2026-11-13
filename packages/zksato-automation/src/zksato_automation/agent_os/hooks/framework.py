"""Hook framework for ZKSATO agent orchestration.

Provides a typed lifecycle event framework for agent orchestration.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    """Lifecycle hook events."""

    # Session events
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    SESSION_PAUSE = "session.pause"
    SESSION_RESUME = "session.resume"

    # Plan events
    PLAN_CREATED = "plan.created"
    PLAN_STARTED = "plan.started"
    PLAN_PHASE_CHANGED = "plan.phase_changed"
    PLAN_COMPLETED = "plan.completed"
    PLAN_FAILED = "plan.failed"
    PLAN_CANCELLED = "plan.cancelled"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRY = "task.retry"
    TASK_APPROVAL_REQUESTED = "task.approval_requested"
    TASK_APPROVED = "task.approved"
    TASK_REJECTED = "task.rejected"

    # Approval gate events
    GATE_PENDING = "gate.pending"
    GATE_APPROVED = "gate.approved"
    GATE_REJECTED = "gate.rejected"

    # File events
    BEFORE_FILE_READ = "file.read.before"
    AFTER_FILE_READ = "file.read.after"
    BEFORE_FILE_WRITE = "file.write.before"
    AFTER_FILE_WRITE = "file.write.after"
    BEFORE_FILE_MODIFY = "file.modify.before"
    AFTER_FILE_MODIFY = "file.modify.after"
    BEFORE_FILE_DELETE = "file.delete.before"
    AFTER_FILE_DELETE = "file.delete.after"

    # Command events
    BEFORE_COMMAND = "command.before"
    AFTER_COMMAND = "command.after"

    # Tool events
    BEFORE_TOOL = "tool.before"
    AFTER_TOOL = "tool.after"

    # Model events
    BEFORE_MODEL_REQUEST = "model.request.before"
    AFTER_MODEL_RESPONSE = "model.response.after"

    # Error events
    ERROR = "error"
    WARNING = "warning"


class HookPriority(int, Enum):
    """Hook execution priority (higher runs first)."""

    CRITICAL = 1000
    HIGH = 100
    NORMAL = 50
    LOW = 10
    BACKGROUND = 0


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    event: HookEvent
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None
    plan_id: str | None = None
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from data."""
        return self.data.get(key, default)


@dataclass
class HookResult:
    """Result of hook execution."""

    hook_id: str
    event: HookEvent
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    modified_data: dict[str, Any] | None = None


@dataclass
class HookRegistration:
    """A registered hook."""

    hook_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event: HookEvent
    handler: Callable[[HookContext], Awaitable[Any]]
    name: str = ""
    description: str = ""
    priority: HookPriority = HookPriority.NORMAL
    timeout_seconds: float = 30.0
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def matches(self, context: HookContext) -> bool:
        """Check if hook matches the context."""
        if not self.enabled:
            return False

        # Check conditions
        for key, expected in self.conditions.items():
            actual = context.data.get(key)
            if actual != expected:
                return False

        return True


class HookRegistry:
    """Registry for managing hooks."""

    def __init__(self) -> None:
        self._hooks: dict[str, HookRegistration] = {}
        self._event_index: dict[str, list[str]] = {}  # event -> hook_ids

    def register(self, hook: HookRegistration) -> str:
        """Register a hook."""
        self._hooks[hook.hook_id] = hook
        if hook.event.value not in self._event_index:
            self._event_index[hook.event.value] = []
        self._event_index[hook.event.value].append(hook.hook_id)
        # Sort by priority (highest first)
        self._event_index[hook.event.value].sort(
            key=lambda hid: self._hooks[hid].priority.value,
            reverse=True,
        )
        logger.info("Registered hook: %s for %s", hook.name, hook.event.value)
        return hook.hook_id

    def unregister(self, hook_id: str) -> bool:
        """Unregister a hook."""
        if hook_id not in self._hooks:
            return False
        hook = self._hooks.pop(hook_id)
        if hook.event.value in self._event_index:
            self._event_index[hook.event.value].remove(hook_id)
        logger.info("Unregistered hook: %s", hook_id)
        return True

    def get_hook(self, hook_id: str) -> HookRegistration | None:
        """Get a hook by ID."""
        return self._hooks.get(hook_id)

    def get_hooks_for_event(self, event: HookEvent) -> list[HookRegistration]:
        """Get all hooks for an event, sorted by priority."""
        hook_ids = self._event_index.get(event.value, [])
        return [self._hooks[hid] for hid in hook_ids]

    def list_hooks(self, event: HookEvent | None = None) -> list[HookRegistration]:
        """List all hooks, optionally filtered by event."""
        if event:
            return self.get_hooks_for_event(event)
        return list(self._hooks.values())

    def enable_hook(self, hook_id: str) -> bool:
        """Enable a hook."""
        if hook_id in self._hooks:
            self._hooks[hook_id].enabled = True
            return True
        return False

    def disable_hook(self, hook_id: str) -> bool:
        """Disable a hook."""
        if hook_id in self._hooks:
            self._hooks[hook_id].enabled = False
            return True
        return False


class HookExecutor:
    """Executes hooks with timeout, error handling, and audit logging."""

    def __init__(self, registry: HookRegistry, audit_logger: logging.Logger | None = None) -> None:
        self.registry = registry
        self.audit_logger = audit_logger or logger

    async def execute(
        self,
        event: HookEvent,
        context: HookContext,
        stop_on_error: bool = False,
    ) -> list[HookResult]:
        """Execute all hooks for an event."""
        hooks = self.registry.get_hooks_for_event(event)
        if not hooks:
            return []

        # Filter matching hooks
        matching = [h for h in hooks if h.matches(context)]
        if not matching:
            return []

        results = []

        for hook in matching:
            if not self.registry._hooks[hook.hook_id].enabled:
                continue

            result = await self._execute_hook(hook, context)
            results.append(result)

            # Update context with modified data
            if result.modified_data:
                context.data.update(result.modified_data)

            # Handle errors
            if not result.success and stop_on_error:
                self._log_audit(hook, result)
                break

            # Log audit
            self._log_audit(hook, result)

        return results

    async def _execute_hook(self, hook: HookRegistration, context: HookContext) -> HookResult:
        """Execute a single hook with timeout."""
        start = datetime.now(UTC)

        try:
            if hook.handler:
                output = await asyncio.wait_for(
                    hook.handler(context),
                    timeout=hook.timeout_seconds,
                )
            else:
                output = None

            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return HookResult(
                hook_id=hook.hook_id,
                event=hook.event,
                success=True,
                output=output,
                duration_ms=duration,
            )

        except TimeoutError:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return HookResult(
                hook_id=hook.hook_id,
                event=hook.event,
                success=False,
                error=f"Hook timed out after {hook.timeout_seconds}s",
                duration_ms=duration,
            )

        except Exception as exc:
            duration = (datetime.now(UTC) - start).total_seconds() * 1000
            return HookResult(
                hook_id=hook.hook_id,
                event=hook.event,
                success=False,
                error=str(exc),
                duration_ms=duration,
            )

    def _log_audit(self, hook: HookRegistration, result: HookResult) -> None:
        """Log hook execution for audit."""
        self.audit_logger.info(
            "Hook executed: %s | event=%s | success=%s | duration=%.1fms",
            hook.name,
            result.event.value,
            result.success,
            result.duration_ms,
        )


class HookManager:
    """High-level hook management."""

    def __init__(self, audit_log_path: Path | None = None) -> None:
        self.registry = HookRegistry()
        self.executor = HookExecutor(self.registry)
        self._audit_logger = self._setup_audit_logger(audit_log_path)

    def _setup_audit_logger(self, log_path: Path | None) -> logging.Logger:
        audit_logger = logging.getLogger("zksato.hooks.audit")
        audit_logger.setLevel(logging.INFO)

        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
            audit_logger.addHandler(handler)

        return audit_logger

    def register_hook(
        self,
        event: HookEvent,
        handler: Callable[[HookContext], Awaitable[Any]],
        name: str = "",
        description: str = "",
        priority: HookPriority = HookPriority.NORMAL,
        timeout_seconds: float = 30.0,
        conditions: dict[str, Any] | None = None,
        tags: set[str] | None = None,
    ) -> str:
        """Register a hook."""
        hook = HookRegistration(
            event=event,
            handler=handler,
            name=name or handler.__name__,
            description=description,
            priority=priority,
            timeout_seconds=timeout_seconds,
            conditions=conditions or {},
            tags=tags or set(),
        )
        return self.registry.register(hook)

    def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a hook."""
        return self.registry.unregister(hook_id)

    def get_hooks(self, event: HookEvent | None = None) -> list[HookRegistration]:
        """List hooks."""
        return self.registry.list_hooks(event)

    def enable_hook(self, hook_id: str) -> bool:
        """Enable a hook."""
        return self.registry.enable_hook(hook_id)

    def disable_hook(self, hook_id: str) -> bool:
        """Disable a hook."""
        return self.registry.disable_hook(hook_id)

    async def emit(
        self,
        event: HookEvent,
        context: HookContext,
        stop_on_error: bool = False,
    ) -> list[HookResult]:
        """Emit an event and execute all matching hooks."""
        return await self.executor.execute(event, context, stop_on_error)

    async def emit_simple(
        self,
        event: HookEvent,
        session_id: str | None = None,
        plan_id: str | None = None,
        task_id: str | None = None,
        data: dict[str, Any] | None = None,
        stop_on_error: bool = False,
    ) -> list[HookResult]:
        """Emit an event with simple parameters."""
        context = HookContext(
            event=event,
            session_id=session_id,
            plan_id=plan_id,
            task_id=task_id,
            data=data or {},
        )
        return await self.emit(event, context, stop_on_error)


# Built-in hooks
async def log_session_start(context: HookContext) -> None:
    """Log session start."""
    logger.info("Session started: %s", context.session_id)


async def log_session_end(context: HookContext) -> None:
    """Log session end."""
    logger.info("Session ended: %s", context.session_id)


async def log_plan_created(context: HookContext) -> None:
    """Log plan creation."""
    logger.info("Plan created: %s (%s)", context.plan_id, context.data.get("objective", ""))


async def log_task_started(context: HookContext) -> None:
    """Log task start."""
    logger.info("Task started: %s (%s)", context.task_id, context.data.get("task_type", ""))


async def log_task_completed(context: HookContext) -> None:
    """Log task completion."""
    logger.info("Task completed: %s", context.task_id)


async def log_file_write(context: HookContext) -> None:
    """Log file write."""
    logger.info("File written: %s", context.data.get("path", ""))


async def validate_file_write(context: HookContext) -> dict[str, Any] | None:
    """Validate file write (example validation hook)."""
    path = context.data.get("path", "")
    content = context.data.get("content", "")

    # Example: Prevent writing to sensitive paths
    sensitive_paths = [".env", "secrets", "credentials", "private.key"]
    for sensitive in sensitive_paths:
        if sensitive in path.lower():
            return {"error": f"Blocked write to sensitive path: {path}"}

    # Example: Limit file size
    if len(content) > 10_000_000:  # 10MB
        return {"error": f"File too large: {len(content)} bytes"}

    return None


async def check_command_safety(context: HookContext) -> dict[str, Any] | None:
    """Check command safety before execution."""
    command = context.data.get("command", "")

    # Dangerous patterns
    dangerous = [
        "rm -rf /",
        "dd if=",
        "mkfs",
        ":(){ :|:& };:",  # Fork bomb
        "chmod 777",
        "chown root",
    ]

    for pattern in dangerous:
        if pattern in command:
            return {"error": f"Blocked dangerous command pattern: {pattern}"}

    return None


def setup_builtin_hooks(manager: HookManager) -> None:
    """Register built-in hooks."""
    manager.register_hook(
        HookEvent.SESSION_START,
        log_session_start,
        name="log_session_start",
        description="Log session start",
        priority=HookPriority.HIGH,
    )

    manager.register_hook(
        HookEvent.SESSION_END,
        log_session_end,
        name="log_session_end",
        description="Log session end",
        priority=HookPriority.HIGH,
    )

    manager.register_hook(
        HookEvent.PLAN_CREATED,
        log_plan_created,
        name="log_plan_created",
        description="Log plan creation",
        priority=HookPriority.NORMAL,
    )

    manager.register_hook(
        HookEvent.TASK_STARTED,
        log_task_started,
        name="log_task_started",
        description="Log task start",
        priority=HookPriority.NORMAL,
    )

    manager.register_hook(
        HookEvent.TASK_COMPLETED,
        log_task_completed,
        name="log_task_completed",
        description="Log task completion",
        priority=HookPriority.NORMAL,
    )

    manager.register_hook(
        HookEvent.BEFORE_FILE_WRITE,
        validate_file_write,
        name="validate_file_write",
        description="Validate file writes for safety",
        priority=HookPriority.CRITICAL,
        timeout_seconds=10.0,
    )

    manager.register_hook(
        HookEvent.BEFORE_COMMAND,
        check_command_safety,
        name="check_command_safety",
        description="Check command safety before execution",
        priority=HookPriority.CRITICAL,
        timeout_seconds=10.0,
    )

    manager.register_hook(
        HookEvent.AFTER_FILE_WRITE,
        log_file_write,
        name="log_file_write",
        description="Log file writes",
        priority=HookPriority.LOW,
    )
