"""Coordination module for multi-agent orchestration."""

from .orchestrator_v2 import (
    AgentAssignment,
    AgentCoordinator,
    OrchestratorV2,
    Task,
    WorkflowEngine,
)
from .shared_state import (
    CRDTBase,
    GCounter,
    LWWMap,
    LWWRegister,
    ORSet,
    PNCounter,
    SharedStateManager,
    StateSynchronizer,
)

__all__ = [
    "AgentAssignment",
    "AgentCoordinator",
    # Shared state
    "CRDTBase",
    "GCounter",
    "LWWMap",
    "LWWRegister",
    "ORSet",
    # Orchestrator
    "OrchestratorV2",
    "PNCounter",
    "SharedStateManager",
    "StateSynchronizer",
    "Task",
    "WorkflowEngine",
]
