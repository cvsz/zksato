"""Agent OS - Autonomous agent orchestration for zksato."""

from .context.manager import ContextEntry, ContextManager, ContextWindow
from .monitoring.dashboard import (
    AgentStatus,
    OrchestrationMonitor,
    ProviderMonitorData,
    QualityGateResult,
    TaskMonitorData,
    get_monitor,
)
from .orchestrator.main import (
    AgentConfig,
    AutonomousOrchestrator,
    OrchestratorConfig,
)
from .providers.router import (
    LocalProvider,
    ModelMetadata,
    ModelRouter,
    ModelRouterWithFallback,
    ProviderHealth,
    ProviderRegistry,
    ProviderType,
    RoutingContext,
    RoutingDecision,
)
from .security.permissions import (
    Permission,
    PermissionManager,
    SideEffect,
    ToolAuthorization,
    ToolExecutionRecord,
    ToolExecutor,
    ToolSchema,
    setup_builtin_tools,
)
from .tasks.executor import TaskExecutor, create_task_plan
from .tasks.persistence import TaskEventLogger, TaskStore
from .tasks.state import (
    Task,
    TaskDependency,
    TaskPlan,
    TaskPriority,
    TaskResult,
    TaskState,
    TaskType,
)

__all__ = [
    # Orchestrator
    "AgentConfig",
    "AutonomousOrchestrator",
    "OrchestratorConfig",
    # Tasks
    "TaskExecutor",
    "create_task_plan",
    "TaskEventLogger",
    "TaskStore",
    "Task",
    "TaskDependency",
    "TaskPlan",
    "TaskPriority",
    "TaskResult",
    "TaskState",
    "TaskType",
    # Context
    "ContextEntry",
    "ContextManager",
    "ContextWindow",
    # Providers
    "LocalProvider",
    "ModelMetadata",
    "ModelRouter",
    "ModelRouterWithFallback",
    "ProviderHealth",
    "ProviderRegistry",
    "ProviderType",
    "RoutingContext",
    "RoutingDecision",
    # Monitoring
    "AgentStatus",
    "OrchestrationMonitor",
    "ProviderMonitorData",
    "QualityGateResult",
    "TaskMonitorData",
    "get_monitor",
    # Security
    "Permission",
    "PermissionManager",
    "ToolExecutor",
    "ToolSchema",
    "ToolAuthorization",
    "ToolExecutionRecord",
    "SideEffect",
    "setup_builtin_tools",
]
