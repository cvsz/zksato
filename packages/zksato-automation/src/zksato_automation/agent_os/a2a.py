"""A2A (Agent-to-Agent) protocol for zksato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from zksato_core.ids import new_ulid


class A2AMessageType(str, Enum):
    """A2A message types."""

    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    HEARTBEAT = "heartbeat"


@dataclass
class A2AMessage:
    """A2A protocol message."""

    message_id: UUID = field(default_factory=new_ulid)
    from_agent: str = ""
    to_agent: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    message_type: A2AMessageType = A2AMessageType.REQUEST
    correlation_id: UUID | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    name: str
    capabilities: set[str] = field(default_factory=set)
    status: str = "active"
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))


class AgentRegistry:
    """Registry for A2A agents."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentInfo] = {}
        self._message_handlers: dict[str, list[Callable]] = {}

    def register(self, agent: AgentInfo) -> None:
        """Register an agent."""
        self.agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent info."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[AgentInfo]:
        """List all agents."""
        return list(self.agents.values())

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    async def send_message(self, message: A2AMessage) -> A2AMessage | None:
        """Send a message to an agent."""
        target = self.agents.get(message.to_agent)
        if not target:
            return A2AMessage(
                from_agent="system",
                to_agent=message.from_agent,
                message_type=A2AMessageType.RESPONSE,
                correlation_id=message.message_id,
                payload={"error": "Agent not found"},
            )

        # Call handlers
        handlers = self._message_handlers.get(message.message_type.value, [])
        for handler in handlers:
            try:
                await handler(message, target)
            except Exception:
                pass  # Log in production

        return None  # Would return response in real implementation

    async def broadcast(self, message: A2AMessage) -> None:
        """Broadcast message to all agents."""
        for agent in self.agents.values():
            if agent.agent_id != message.from_agent:
                msg = A2AMessage(
                    from_agent=message.from_agent,
                    to_agent=agent.agent_id,
                    payload=message.payload,
                    message_type=message.message_type,
                    correlation_id=message.correlation_id,
                )
                await self.send_message(msg)
