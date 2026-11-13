"""Event-sourced agent session for zksato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from zksato_core.ids import new_uuid


class AgentEventType(str, Enum):
    """Types of agent events."""

    SESSION_CREATED = "session.created"
    SESSION_STARTED = "session.started"
    SESSION_STOPPED = "session.stopped"
    TOOL_EXECUTED = "tool.executed"
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_REJECTED = "order.rejected"
    RISK_CHECK = "risk.check"
    SKILL_EXECUTED = "skill.executed"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Event in an agent session."""

    event_id: UUID = field(default_factory=new_uuid)
    session_id: UUID = field(default_factory=new_uuid)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: AgentEventType = AgentEventType.SESSION_CREATED
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID | None = None


class SessionState(str, Enum):
    """Session lifecycle states."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentSession:
    """Event-sourced agent session."""

    session_id: UUID
    subaccount_id: str
    events: list[AgentEvent] = field(default_factory=list)
    state: SessionState = SessionState.CREATED
    _current_skill: str | None = None
    _pending_orders: list[Any] = field(default_factory=list)

    def append_event(self, event: AgentEvent) -> None:
        """Append an event to the session log."""
        self.events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: AgentEvent) -> None:
        """Apply event to session state."""
        if event.event_type == AgentEventType.SESSION_STARTED:
            self.state = SessionState.RUNNING
        elif event.event_type == AgentEventType.SESSION_STOPPED:
            self.state = SessionState.STOPPED
        elif event.event_type == AgentEventType.ERROR:
            self.state = SessionState.ERROR

    def start(self) -> None:
        """Start the session."""
        self.append_event(
            AgentEvent(
                session_id=self.session_id,
                event_type=AgentEventType.SESSION_STARTED,
            )
        )

    def stop(self) -> None:
        """Stop the session."""
        self.append_event(
            AgentEvent(
                session_id=self.session_id,
                event_type=AgentEventType.SESSION_STOPPED,
            )
        )

    def get_events(self, event_type: AgentEventType | None = None) -> list[AgentEvent]:
        """Get events, optionally filtered by type."""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events

    def get_state(self) -> dict[str, Any]:
        """Get session state snapshot."""
        return {
            "session_id": str(self.session_id),
            "subaccount_id": self.subaccount_id,
            "state": self.state.value,
            "event_count": len(self.events),
            "pending_orders": len(self._pending_orders),
        }
