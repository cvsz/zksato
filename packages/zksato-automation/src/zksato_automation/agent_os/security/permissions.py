"""Security and tool permission system for autonomous agents."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from zksato_core.ids import new_uuid  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Tool permissions."""

    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_SHELL = "execute_shell"
    NETWORK_REQUEST = "network_request"
    GIT_OPERATIONS = "git_operations"
    CREDENTIAL_ACCESS = "credential_access"
    EXTERNAL_API = "external_api"
    DATABASE_ACCESS = "database_access"
    PROCESS_MANAGEMENT = "process_management"
    SYSTEM_CONFIG = "system_config"


class SideEffect(str, Enum):
    """Side effect classification."""

    NONE = "none"  # Pure function, no side effects
    READ_ONLY = "read_only"  # Reads state but doesn't modify
    LOCAL_WRITE = "local_write"  # Writes to local filesystem
    NETWORK = "network"  # Makes network requests
    STATE_CHANGE = "state_change"  # Changes application state
    DESTRUCTIVE = "destructive"  # Irreversible changes (delete, etc.)
    PRIVILEGED = "privileged"  # Requires elevated permissions


@dataclass
class ToolSchema:
    """Tool schema definition."""

    tool_id: str
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    output_schema: dict[str, Any]  # JSON Schema
    required_permissions: set[Permission] = field(default_factory=set)
    side_effect: SideEffect = SideEffect.NONE
    timeout_seconds: float = 30.0
    max_memory_mb: int = 512
    max_cpu_seconds: float = 10.0
    requires_confirmation: bool = False
    allowed_agents: list[str] | None = None  # None = all agents
    tags: set[str] = field(default_factory=set)


@dataclass
class ToolAuthorization:
    """Tool authorization."""

    tool_id: str
    agent_id: str
    granted: bool
    granted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    granted_by: str = "system"
    conditions: dict[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None


@dataclass
class ToolExecutionRecord:
    """Record of tool execution."""

    execution_id: UUID = field(default_factory=new_uuid)
    tool_id: str = ""
    agent_id: str = ""
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    permissions_used: set[Permission] = field(default_factory=set)
    side_effect: SideEffect = SideEffect.NONE
    authorized: bool = False


class PermissionManager:
    """Manages tool permissions and authorizations."""

    def __init__(self) -> None:
        self._tool_schemas: dict[str, ToolSchema] = {}
        self._authorizations: dict[
            str, dict[str, ToolAuthorization]
        ] = {}  # agent_id -> tool_id -> auth
        self._execution_history: list[ToolExecutionRecord] = []
        self._default_permissions: set[Permission] = {
            Permission.READ_FILES,
            Permission.NETWORK_REQUEST,
        }

    def register_tool(self, schema: ToolSchema) -> None:
        """Register a tool schema."""
        self._tool_schemas[schema.tool_id] = schema
        logger.info("Registered tool: %s", schema.tool_id)

    def get_tool_schema(self, tool_id: str) -> ToolSchema | None:
        """Get tool schema."""
        return self._tool_schemas.get(tool_id)

    def list_tools(self, agent_id: str | None = None) -> list[ToolSchema]:
        """List available tools for an agent."""
        tools = list(self._tool_schemas.values())
        if agent_id:
            tools = [t for t in tools if t.allowed_agents is None or agent_id in t.allowed_agents]
        return tools

    def authorize_tool(
        self,
        agent_id: str,
        tool_id: str,
        granted: bool = True,
        granted_by: str = "system",
        conditions: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> ToolAuthorization:
        """Authorize a tool for an agent."""
        if agent_id not in self._authorizations:
            self._authorizations[agent_id] = {}

        auth = ToolAuthorization(
            tool_id=tool_id,
            agent_id=agent_id,
            granted=granted,
            granted_by=granted_by,
            conditions=conditions or {},
            expires_at=expires_at,
        )
        self._authorizations[agent_id][tool_id] = auth
        logger.info(
            "Tool %s %s for agent %s", tool_id, "authorized" if granted else "denied", agent_id
        )
        return auth

    def is_authorized(self, agent_id: str, tool_id: str) -> bool:
        """Check if agent is authorized for tool."""
        # Check explicit authorization
        agent_auths = self._authorizations.get(agent_id, {})
        auth = agent_auths.get(tool_id)
        if auth is not None:
            if not auth.granted:
                return False
            return not (auth.expires_at and auth.expires_at < datetime.now(UTC))

        # Check default permissions
        schema = self._tool_schemas.get(tool_id)
        if not schema:
            return False

        # If tool requires no special permissions, allow by default
        if not schema.required_permissions:
            return True

        # Check if agent has default permissions covering tool requirements
        return schema.required_permissions.issubset(self._default_permissions)

    def grant_permission(self, agent_id: str, permission: Permission) -> None:
        """Grant a permission to an agent."""
        self._default_permissions.add(permission)

    def revoke_permission(self, agent_id: str, permission: Permission) -> None:
        """Revoke a permission from an agent."""
        self._default_permissions.discard(permission)

    def record_execution(self, record: ToolExecutionRecord) -> None:
        """Record tool execution."""
        self._execution_history.append(record)
        # Keep last 10000 records
        if len(self._execution_history) > 10000:
            self._execution_history = self._execution_history[-10000:]

    def get_execution_history(
        self,
        agent_id: str | None = None,
        tool_id: str | None = None,
        limit: int = 100,
    ) -> list[ToolExecutionRecord]:
        """Get execution history."""
        history = self._execution_history
        if agent_id:
            history = [r for r in history if r.agent_id == agent_id]
        if tool_id:
            history = [r for r in history if r.tool_id == tool_id]
        return history[-limit:]


class ToolExecutor:
    """Secure tool executor with permission checking."""

    def __init__(self, permission_manager: PermissionManager) -> None:
        self.permission_manager = permission_manager
        self._tool_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}

    def register_handler(
        self,
        tool_id: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a tool handler."""
        schema = self.permission_manager.get_tool_schema(tool_id)
        if not schema:
            raise ValueError(f"Tool schema not registered: {tool_id}")
        self._tool_handlers[tool_id] = handler

    async def execute(
        self,
        agent_id: str,
        tool_id: str,
        input_data: dict[str, Any],
    ) -> ToolExecutionRecord:
        """Execute a tool with permission checking."""
        import time

        start = time.time()
        record = ToolExecutionRecord(
            tool_id=tool_id,
            agent_id=agent_id,
            input_data=input_data,
        )

        # Check authorization
        if not self.permission_manager.is_authorized(agent_id, tool_id):
            record.error = f"Agent {agent_id} not authorized for tool {tool_id}"
            record.authorized = False
            self.permission_manager.record_execution(record)
            raise PermissionError(record.error)

        record.authorized = True
        schema = self.permission_manager.get_tool_schema(tool_id)
        if schema:
            record.permissions_used = schema.required_permissions
            record.side_effect = schema.side_effect

        # Execute with timeout
        handler = self._tool_handlers.get(tool_id)
        if not handler:
            record.error = f"No handler for tool: {tool_id}"
            self.permission_manager.record_execution(record)
            raise ValueError(record.error)

        try:
            # Apply timeout
            output = await asyncio.wait_for(
                handler(input_data),
                timeout=schema.timeout_seconds if schema else 30.0,
            )
            record.output_data = output
            record.error = None
        except TimeoutError:
            record.error = f"Tool timed out after {schema.timeout_seconds if schema else 30.0}s"
        except Exception as exc:
            record.error = f"Tool execution failed: {exc}"

        record.completed_at = datetime.now(UTC)
        record.duration_ms = (time.time() - start) * 1000

        self.permission_manager.record_execution(record)
        return record


# Built-in tool schemas
BUILTIN_TOOLS: list[ToolSchema] = [
    ToolSchema(
        tool_id="read_file",
        name="Read File",
        description="Read a file from the filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "size": {"type": "integer"},
            },
        },
        required_permissions={Permission.READ_FILES},
        side_effect=SideEffect.READ_ONLY,
        timeout_seconds=10.0,
    ),
    ToolSchema(
        tool_id="write_file",
        name="Write File",
        description="Write content to a file",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path", "content"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "bytes_written": {"type": "integer"},
            },
        },
        required_permissions={Permission.WRITE_FILES},
        side_effect=SideEffect.LOCAL_WRITE,
        timeout_seconds=10.0,
        requires_confirmation=True,
    ),
    ToolSchema(
        tool_id="execute_shell",
        name="Execute Shell Command",
        description="Execute a shell command",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}},
                "cwd": {"type": "string"},
                "env": {"type": "object"},
            },
            "required": ["command"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "returncode": {"type": "integer"},
            },
        },
        required_permissions={Permission.EXECUTE_SHELL},
        side_effect=SideEffect.DESTRUCTIVE,
        timeout_seconds=60.0,
        requires_confirmation=True,
    ),
    ToolSchema(
        tool_id="git_operations",
        name="Git Operations",
        description="Perform git operations",
        input_schema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "Git operation (status, diff, add, commit, branch, checkout, tag, log, diff, worktree)"},
                "args": {"type": "array", "description": "Arguments for the git operation"},
                "repo_path": {"type": "string", "description": "Repository path"},
            },
            "required": ["operation"],
        },
        output_schema={"success": {"type": "boolean"}, "output": {"type": "string"}, "returncode": {"type": "integer"}},
        required_permissions={Permission.GIT_OPERATIONS},
        side_effect=SideEffect.LOCAL_WRITE,
        timeout_seconds=30.0,
    ),
    ToolSchema(
        tool_id="git_change_tracking",
        name="Git Change Tracking",
        description="Track and analyze git repository changes",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action (capture_state, get_history, get_diff_between)"},
                "params": {"type": "object", "description": "Optional parameters"},
            },
            "required": ["action"],
        },
        output_schema={"success": {"type": "boolean"}, "state": {"type": "object"}, "history": {"type": "array"}, "difference": {"type": "object"}},
        required_permissions={Permission.GIT_OPERATIONS},
        side_effect=SideEffect.LOCAL_WRITE,
        timeout_seconds=30.0,
    ),
    ToolSchema(
        tool_id="git_hooks",
        name="Git Hooks",
        description="Run git pre-commit and post-commit hooks",
        input_schema={
            "type": "object",
            "properties": {
                "hook_type": {"type": "string", "description": "Hook type (pre_commit, post_commit, check_safety)"},
                "commit_hash": {"type": "string", "description": "Optional commit hash"},
                "repo_path": {"type": "string", "description": "Repository path"},
            },
            "required": ["hook_type"],
        },
        output_schema={"success": {"type": "boolean"}, "output": {"type": "string"}, "results": {"type": "array"}},
        required_permissions={Permission.GIT_OPERATIONS},
        side_effect=SideEffect.LOCAL_WRITE,
        timeout_seconds=30.0,
    ),
    ToolSchema(
        tool_id="http_request",
        name="HTTP Request",
        description="Make an HTTP request",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "default": "GET"},
                "headers": {"type": "object"},
                "body": {"type": "string"},
                "timeout": {"type": "number", "default": 30.0},
            },
            "required": ["url"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "headers": {"type": "object"},
                "body": {"type": "string"},
            },
        },
        required_permissions={Permission.NETWORK_REQUEST},
        side_effect=SideEffect.NETWORK,
        timeout_seconds=30.0,
    ),
]


def setup_builtin_tools(permission_manager: PermissionManager, tool_executor: ToolExecutor) -> None:
    """Set up built-in tools."""
    for schema in BUILTIN_TOOLS:
        permission_manager.register_tool(schema)

    # Register handlers
    async def read_file_handler(data: dict[str, Any]) -> dict[str, Any]:
        path = data["path"]
        encoding = data.get("encoding", "utf-8")
        with Path(path).open(encoding=encoding) as f:
            content = f.read()
        return {"content": content, "size": len(content)}

    async def write_file_handler(data: dict[str, Any]) -> dict[str, Any]:
        path = data["path"]
        content = data["content"]
        encoding = data.get("encoding", "utf-8")
        with Path(path).open("w", encoding=encoding) as f:
            f.write(content)
        return {"success": True, "bytes_written": len(content.encode(encoding))}

    async def execute_shell_handler(data: dict[str, Any]) -> dict[str, Any]:
        command = data["command"]
        args = data.get("args", [])
        cwd = data.get("cwd")
        env = data.get("env")

        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8") if stdout else "",
            "stderr": stderr.decode("utf-8") if stderr else "",
            "returncode": proc.returncode,
        }

    async def git_operations_handler(data: dict[str, Any]) -> dict[str, Any]:
        """Handle git operations using the GitClient."""
        from zksato_automation.agent_os.git import get_client

        client = get_client(data.get("repo_path", "."))
        operation = data["operation"]
        args = data.get("args", [])

        result = await client.run(operation, *args)
        return {
            "success": result.success,
            "output": result.stdout,
            "returncode": result.returncode,
        }

    async def git_change_tracking_handler(data: dict[str, Any]) -> dict[str, Any]:
        """Handle git change tracking."""
        from zksato_automation.agent_os.git import get_tracker

        tracker = get_tracker(get_client(data.get("repo_path", ".")))
        action = data["action"]
        params = data.get("params", {})

        if action == "capture_state":
            state = await tracker.capture_state()
            return {
                "success": True,
                "state": state.to_dict(),
            }
        elif action == "get_history":
            history = await tracker.get_history()
            return {
                "success": True,
                "history": [s.to_dict() for s in history],
            }
        elif action == "get_diff_between":
            idx1 = params.get("index1", 0)
            idx2 = params.get("index2", 1)
            diff = await tracker.get_diff_between(idx1, idx2)
            return {
                "success": True,
                "difference": diff,
            }
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def git_hooks_handler(data: dict[str, Any]) -> dict[str, Any]:
        """Handle git hooks."""
        from zksato_automation.agent_os.git import run_pre_commit_hooks, run_post_commit_hooks, check_commit_safety

        hook_type = data["hook_type"]
        commit_hash = data.get("commit_hash")
        repo_path = data.get("repo_path", ".")

        if hook_type == "pre_commit":
            result = await run_pre_commit_hooks(repo_path)
            return {
                "success": result.success,
                "output": result.stdout,
            }
        elif hook_type == "post_commit":
            result = await run_post_commit_hooks(repo_path, commit_hash)
            return {
                "success": result.success,
                "output": result.stdout,
            }
        elif hook_type == "check_safety":
            result = await check_commit_safety(repo_path)
            return {
                "success": result.success,
                "output": result.stdout,
            }
        else:
            return {"success": False, "error": f"Unknown hook type: {hook_type}"}

    tool_executor.register_handler("read_file", read_file_handler)
    tool_executor.register_handler("write_file", write_file_handler)
    tool_executor.register_handler("execute_shell", execute_shell_handler)
    tool_executor.register_handler("git_operations", git_operations_handler)
    tool_executor.register_handler("git_change_tracking", git_change_tracking_handler)
    tool_executor.register_handler("git_hooks", git_hooks_handler)
    tool_executor.register_handler("http_request", http_request_handler)