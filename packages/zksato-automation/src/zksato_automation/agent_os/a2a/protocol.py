"""A2A (Agent-to-Agent) Protocol for ZKSATO.

Implements agent-to-agent communication protocol with:
- Message routing and delivery
- Capability discovery and negotiation
- Session management
- Message serialization/deserialization
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class A2AMessageType(str, Enum):
    """A2A message types."""

    # Discovery
    DISCOVER = "discover"
    DISCOVER_RESPONSE = "discover_response"

    # Capability negotiation
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    CAPABILITY_NEGOTIATE = "capability_negotiate"

    # Task management
    TASK_REQUEST = "task_request"
    TASK_ACCEPT = "task_accept"
    TASK_REJECT = "task_reject"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TASK_CANCEL = "task_cancel"

    # State synchronization
    STATE_SYNC = "state_sync"
    STATE_DELTA = "state_delta"
    STATE_REQUEST = "state_request"
    STATE_RESPONSE = "state_response"

    # Handoff
    HANDOFF_REQUEST = "handoff_request"
    HANDOFF_ACCEPT = "handoff_accept"
    HANDOFF_REJECT = "handoff_reject"
    HANDOFF_COMPLETE = "handoff_complete"

    # Health/Status
    HEARTBEAT = "heartbeat"
    HEALTH_CHECK = "health_check"
    HEALTH_RESPONSE = "health_response"
    STATUS_UPDATE = "status_update"

    # Error
    ERROR = "error"


@dataclass
class A2AMessage:
    """A2A protocol message."""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: A2AMessageType = A2AMessageType.DISCOVER
    sender_id: str = ""
    recipient_id: str = ""  # Empty for broadcast
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl: int = 30  # Time to live in seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AMessage:
        """Deserialize from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=A2AMessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id", ""),
            correlation_id=data.get("correlation_id"),
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl=data.get("ttl", 30),
        )

    def is_expired(self) -> bool:
        """Check if message has expired."""
        age = (datetime.now(UTC) - self.timestamp).total_seconds()
        return age > self.ttl


class AgentCapability(str, Enum):
    """Standard agent capabilities."""

    # Core
    TASK_EXECUTION = "task_execution"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    CODE_REVIEW = "code_review"
    SECURITY_AUDIT = "security_audit"
    DOCUMENTATION = "documentation"

    # Specialized
    ARCHITECTURE_DESIGN = "architecture_design"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DATABASE_DESIGN = "database_design"
    API_DESIGN = "api_design"
    DEVOPS = "devops"
    DATA_ANALYSIS = "data_analysis"
    ML_ENGINEERING = "ml_engineering"
    TECHNOLOGY_SELECTION = "technology_selection"
    SYSTEM_DESIGN = "system_design"
    THREAT_MODELING = "threat_modeling"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    COMPLIANCE_CHECKING = "compliance_checking"
    SECRET_DETECTION = "secret_detection"
    STYLE_CHECKING = "style_checking"
    BUG_DETECTION = "bug_detection"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    COMPLEXITY_ANALYSIS = "complexity_analysis"
    COVERAGE_ANALYSIS = "coverage_analysis"
    FLAKE_DETECTION = "flake_detection"
    TEST_MAINTENANCE = "test_maintenance"
    DOCUMENTATION_GENERATION = "documentation_generation"
    API_DOCUMENTATION = "api_documentation"
    ADR_MANAGEMENT = "adr_management"
    README_GENERATION = "readme_generation"
    CHANGELOG_GENERATION = "changelog_generation"

    # Infrastructure
    FILE_OPERATIONS = "file_operations"
    COMMAND_EXECUTION = "command_execution"
    GIT_OPERATIONS = "git_operations"
    MCP_CLIENT = "mcp_client"
    DATABASE_OPERATIONS = "database_operations"
    NETWORK_OPERATIONS = "network_operations"


@dataclass
class AgentInfo:
    """Information about a registered agent."""

    agent_id: str
    name: str
    role: str
    capabilities: set[AgentCapability] = field(default_factory=set)
    status: str = "idle"  # idle, busy, offline, error
    current_task_id: str | None = None
    endpoint: str | None = None  # For remote agents
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))
    load_factor: float = 0.0  # 0.0 to 1.0

    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        return self.status == "idle" and self.load_factor < 0.8

    def can_handle(self, capability: AgentCapability) -> bool:
        """Check if agent has a capability."""
        return capability in self.capabilities


class AgentRegistry:
    """Registry for A2A agents."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentInfo] = {}
        self._message_handlers: dict[
            A2AMessageType, list[Callable[[A2AMessage], Awaitable[None]]]
        ] = {}
        self._pending_requests: dict[str, asyncio.Future] = {}

    def register(self, agent: AgentInfo) -> None:
        """Register an agent."""
        self.agents[agent.agent_id] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.agent_id)

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info("Unregistered agent: %s", agent_id)
            return True
        return False

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(
        self, status: str | None = None, capability: AgentCapability | None = None
    ) -> list[AgentInfo]:
        """List agents with optional filters."""
        agents = list(self.agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        if capability:
            agents = [a for a in agents if a.can_handle(capability)]
        return agents

    def find_available_agents(self, capability: AgentCapability) -> list[AgentInfo]:
        """Find available agents with a specific capability."""
        return [a for a in self.agents.values() if a.is_available() and a.can_handle(capability)]

    def register_handler(
        self, message_type: A2AMessageType, handler: Callable[[A2AMessage], Awaitable[None]]
    ) -> None:
        """Register a message handler."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    async def send_message(self, message: A2AMessage) -> A2AMessage | None:
        """Send a message to an agent."""
        if message.recipient_id == "broadcast":
            return await self._broadcast(message)

        target = self.agents.get(message.recipient_id)
        if not target:
            return A2AMessage(
                message_type=A2AMessageType.ERROR,
                sender_id="registry",
                recipient_id=message.sender_id,
                correlation_id=message.message_id,
                payload={"error": f"Agent not found: {message.recipient_id}"},
            )

        # Deliver message
        handlers = self._message_handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as exc:
                logger.error("Handler error for %s: %s", message.message_type, exc)

        # Update agent status
        target.last_heartbeat = datetime.now(UTC)
        if message.message_type == A2AMessageType.TASK_REQUEST:
            target.status = "busy"
            target.current_task_id = message.payload.get("task_id")

        return None

    async def _broadcast(self, message: A2AMessage) -> None:
        """Broadcast message to all agents except sender."""
        for agent in self.agents.values():
            if agent.agent_id != message.sender_id:
                msg = A2AMessage(
                    message_id=str(uuid.uuid4()),
                    message_type=message.message_type,
                    sender_id=message.sender_id,
                    recipient_id=agent.agent_id,
                    correlation_id=message.correlation_id,
                    payload=message.payload,
                )
                await self.send_message(msg)

    def register_request(self, correlation_id: str) -> asyncio.Future:
        """Register a pending request."""
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[correlation_id] = future
        return future

    def resolve_request(self, correlation_id: str, response: A2AMessage) -> bool:
        """Resolve a pending request."""
        future = self._pending_requests.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(response)
            return True
        return False


class A2ACommunicator:
    """High-level A2A communication helper."""

    def __init__(self, agent_id: str, registry: AgentRegistry) -> None:
        self.agent_id = agent_id
        self.registry = registry

    async def discover_agents(self, capability: AgentCapability | None = None) -> list[AgentInfo]:
        """Discover available agents."""
        if capability:
            return self.registry.find_available_agents(capability)
        return [a for a in self.registry.agents.values() if a.is_available()]

    async def request_capability(
        self,
        target_agent: str,
        capability: AgentCapability,
        timeout: float = 10.0,
    ) -> bool:
        """Check if an agent has a capability."""
        target = self.registry.get_agent(target_agent)
        if not target:
            return False
        return target.can_handle(capability)

    async def request_task(
        self,
        target_agent: str,
        task_id: str,
        task_type: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> A2AMessage | None:
        """Request another agent to execute a task."""
        message = A2AMessage(
            message_type=A2AMessageType.TASK_REQUEST,
            sender_id=self.agent_id,
            recipient_id=target_agent,
            payload={
                "task_id": task_id,
                "task_type": task_type,
                "payload": payload,
            },
        )

        future = self.registry.register_request(message.correlation_id or message.message_id)
        await self.registry.send_message(message)

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except TimeoutError:
            logger.warning("Task request to %s timed out", target_agent)
            return None

    async def send_progress(
        self,
        target_agent: str,
        task_id: str,
        progress: float,
        message: str = "",
    ) -> None:
        """Send task progress update."""
        message = A2AMessage(
            message_type=A2AMessageType.TASK_PROGRESS,
            sender_id=self.agent_id,
            recipient_id=target_agent,
            payload={
                "task_id": task_id,
                "progress": progress,
                "message": message,
            },
        )
        await self.registry.send_message(message)

    async def send_handoff_request(
        self,
        target_agent: str,
        task_id: str,
        context: dict[str, Any],
        reason: str = "",
    ) -> A2AMessage | None:
        """Request task handoff to another agent."""
        message = A2AMessage(
            message_type=A2AMessageType.HANDOFF_REQUEST,
            sender_id=self.agent_id,
            recipient_id=target_agent,
            payload={
                "task_id": task_id,
                "context": context,
                "reason": reason,
            },
        )

        future = self.registry.register_request(message.message_id)
        await self.registry.send_message(message)

        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except TimeoutError:
            return None

    async def sync_state(
        self,
        target_agent: str,
        state: dict[str, Any],
    ) -> None:
        """Synchronize state with another agent."""
        message = A2AMessage(
            message_type=A2AMessageType.STATE_SYNC,
            sender_id=self.agent_id,
            recipient_id=target_agent,
            payload={"state": state},
        )
        await self.registry.send_message(message)

    async def broadcast_status(self, status: str, metadata: dict[str, Any] | None = None) -> None:
        """Broadcast status to all agents."""
        message = A2AMessage(
            message_type=A2AMessageType.STATUS_UPDATE,
            sender_id=self.agent_id,
            recipient_id="broadcast",
            payload={
                "status": status,
                "metadata": metadata or {},
            },
        )
        await self.registry.send_message(message)

    async def send_heartbeat(self) -> None:
        """Send heartbeat to registry."""
        message = A2AMessage(
            message_type=A2AMessageType.HEARTBEAT,
            sender_id=self.agent_id,
            recipient_id="registry",
            payload={"timestamp": datetime.now(UTC).isoformat()},
        )
        await self.registry.send_message(message)
