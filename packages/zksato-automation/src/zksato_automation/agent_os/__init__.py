"""Agent OS - Autonomous agent orchestration for zksato."""

from .context.manager import ContextEntry, ContextManager, ContextWindow
from .coordination.orchestrator_v2 import OrchestratorV2
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
    # Monitoring
    "AgentStatus",
    "AutonomousOrchestrator",
    # Context
    "ContextEntry",
    "ContextManager",
    "ContextWindow",
    # Providers
    "LocalProvider",
    "ModelMetadata",
    "ModelRouter",
    "ModelRouterWithFallback",
    "OrchestrationMonitor",
    "OrchestratorConfig",
    "OrchestratorV2",
    # Security
    "Permission",
    "PermissionManager",
    "ProviderHealth",
    "ProviderMonitorData",
    "ProviderRegistry",
    "ProviderType",
    "QualityGateResult",
    "RoutingContext",
    "RoutingDecision",
    "SideEffect",
    "Task",
    "TaskDependency",
    "TaskEventLogger",
    # Tasks
    "TaskExecutor",
    "TaskMonitorData",
    "TaskPlan",
    "TaskPriority",
    "TaskResult",
    "TaskState",
    "TaskStore",
    "TaskType",
    "ToolAuthorization",
    "ToolExecutionRecord",
    "ToolExecutor",
    "ToolSchema",
    "create_task_plan",
    "get_monitor",
    "setup_builtin_tools",
]
