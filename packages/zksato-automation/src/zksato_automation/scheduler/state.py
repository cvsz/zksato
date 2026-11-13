"""Checkpoint manager for session recovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from zksato_automation.agent_os.session import (
    AgentEvent,
    AgentEventType,
    AgentSession,
    SessionState,
)


@dataclass
class SessionCheckpoint:
    """Checkpoint for session recovery."""

    session_id: UUID
    subaccount_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    state: SessionState = SessionState.CREATED
    events: list[dict] = field(default_factory=list)
    event_log_position: int = 0
    strategy_state: dict[str, Any] = field(default_factory=dict)
    risk_context: dict[str, Any] = field(default_factory=dict)
    pending_orders: list[dict] = field(default_factory=list)

    @classmethod
    def from_session(cls, session: AgentSession) -> SessionCheckpoint:
        """Create checkpoint from session."""
        return cls(
            session_id=session.session_id,
            subaccount_id=session.subaccount_id,
            state=session.state,
            events=[
                {
                    "event_id": str(e.event_id),
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "payload": e.payload,
                    "correlation_id": str(e.correlation_id) if e.correlation_id else None,
                }
                for e in session.events
            ],
            event_log_position=len(session.events),
            strategy_state={},  # Would be populated from strategy
            risk_context={},  # Would be populated from risk engine
            pending_orders=[],  # Would be populated from order book
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["session_id"] = str(self.session_id)
        data["timestamp"] = self.timestamp.isoformat()
        data["state"] = self.state.value
        return data


class CheckpointStore(Protocol):
    """Protocol for checkpoint storage."""

    async def save(self, checkpoint: SessionCheckpoint) -> None: ...
    async def load(self, session_id: UUID) -> SessionCheckpoint | None: ...


class InMemoryCheckpointStore:
    """In-memory checkpoint store."""

    def __init__(self) -> None:
        self._checkpoints: dict[UUID, SessionCheckpoint] = {}

    async def save(self, checkpoint: SessionCheckpoint) -> None:
        self._checkpoints[checkpoint.session_id] = checkpoint

    async def load(self, session_id: UUID) -> SessionCheckpoint | None:
        return self._checkpoints.get(session_id)


class CheckpointManager:
    """Manages session checkpoints for recovery."""

    def __init__(self, store: CheckpointStore | None = None) -> None:
        self.store = store or InMemoryCheckpointStore()

    async def save_checkpoint(self, session: AgentSession) -> None:
        """Save a checkpoint for a session."""
        checkpoint = SessionCheckpoint.from_session(session)
        await self.store.save(checkpoint)

    async def restore_session(self, session_id: UUID) -> AgentSession | None:
        """Restore a session from checkpoint."""
        checkpoint = await self.store.load(session_id)
        if not checkpoint:
            return None

        session = AgentSession(
            session_id=checkpoint.session_id,
            subaccount_id=checkpoint.subaccount_id,
        )
        session.state = checkpoint.state

        # Restore events
        for event_data in checkpoint.events:
            event = AgentEvent(
                event_id=UUID(event_data["event_id"]),
                session_id=session.session_id,
                event_type=AgentEventType(event_data["event_type"]),
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                payload=event_data["payload"],
                correlation_id=UUID(event_data["correlation_id"])
                if event_data["correlation_id"]
                else None,
            )
            session.events.append(event)

        # Restore other state
        # strategy_state, risk_context, pending_orders would be restored here

        return session

    async def list_checkpoints(self) -> list[SessionCheckpoint]:
        """List all checkpoints (for in-memory store)."""
        if isinstance(self.store, InMemoryCheckpointStore):
            return list(self.store._checkpoints.values())
        return []
