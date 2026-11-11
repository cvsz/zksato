"""Agent-native trading module for zksato.

Inspired by AI-Trader (HKUDS/AI-Trader), this module provides:
- Agent registration, authentication, token-based API
- Agent profiles with cash balance, points, reputation score
- Wallet address integration
- Agent roles and permissions

All features are advisory/research only — order execution always routes
through RiskEngine and TradingService, preserving zksato's safety invariants.
"""

from zksato.agent_trading.models import (
    Agent,
    AgentHeartbeatResponse,
    AgentInfo,
    AgentLoginRequest,
    AgentPasswordResetConfirm,
    AgentPasswordResetRequest,
    AgentRegisterRequest,
    AgentRole,
    AgentTokenRecoveryConfirm,
    AgentTokenRecoveryRequest,
)
from zksato.agent_trading.service import AgentService

__all__ = [
    "Agent",
    "AgentInfo",
    "AgentHeartbeatResponse",
    "AgentLoginRequest",
    "AgentPasswordResetConfirm",
    "AgentPasswordResetRequest",
    "AgentRegisterRequest",
    "AgentRole",
    "AgentService",
    "AgentTokenRecoveryConfirm",
    "AgentTokenRecoveryRequest",
]
