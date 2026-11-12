"""Event base classes and event store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

import orjson

from zksato_core.ids import new_correlation_id
from zksato_core.serialization import json_dumps

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Event:
    """Base event class."""

    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = field(default_factory=new_correlation_id)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json_dumps(
            {
                "id": str(self.id),
                "event_type": self.event_type,
                "timestamp": self.timestamp.isoformat(),
                "correlation_id": self.correlation_id,
                "payload": self.payload,
            }
        )

    @classmethod
    def from_json(cls, data: str) -> Event:
        """Deserialize event from JSON."""
        obj = orjson.loads(data)
        return cls(
            id=UUID(obj["id"]),
            event_type=obj["event_type"],
            timestamp=datetime.fromisoformat(obj["timestamp"]),
            correlation_id=obj["correlation_id"],
            payload=obj["payload"],
        )


@dataclass(frozen=True, slots=True)
class DomainEvent(Event):
    """Domain event with aggregate ID."""

    aggregate_id: UUID = field(default_factory=uuid4)
    aggregate_type: str = ""
    version: int = 1


class EventStore(ABC, Generic[T]):
    """Event store interface."""

    @abstractmethod
    async def append(self, event: T) -> None:
        """Append an event to the store."""
        ...

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> list[T]:
        """Get events for an aggregate."""
        ...

    @abstractmethod
    async def get_events_by_correlation(self, correlation_id: str) -> list[T]:
        """Get events by correlation ID."""
        ...

    @abstractmethod
    async def get_all_events(
        self,
        event_types: list[str] | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        limit: int = 1000,
    ) -> list[T]:
        """Get all events with optional filters."""
        ...


class EventPublisher(ABC):
    """Event publisher interface for publishing events to subscribers."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event."""
        ...

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to an event type."""
        ...

    @abstractmethod
    async def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type."""
        ...


# Common event types
class EventType:
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_ACCEPTED = "order.accepted"
    ORDER_REJECTED = "order.rejected"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_FILLED = "order.filled"
    ORDER_PARTIALLY_FILLED = "order.partially_filled"
    ORDER_NEEDS_RECONCILIATION = "order.needs_reconciliation"

    # Fill events
    FILL_CREATED = "fill.created"

    # Risk events
    RISK_EVALUATED = "risk.evaluated"
    RISK_REJECTED = "risk.rejected"
    KILL_SWITCH_ACTIVATED = "risk.kill_switch_activated"
    KILL_SWITCH_DEACTIVATED = "risk.kill_switch_deactivated"

    # Position events
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    POSITION_UPDATED = "position.updated"

    # Portfolio events
    PORTFOLIO_SNAPSHOT = "portfolio.snapshot"

    # Account events
    ACCOUNT_SNAPSHOT = "account.snapshot"

    # Reconciliation events
    RECONCILIATION_STARTED = "reconciliation.started"
    RECONCILIATION_COMPLETED = "reconciliation.completed"
    RECONCILIATION_DIVERGENCE = "reconciliation.divergence"

    # Bot events
    BOT_STARTED = "bot.started"
    BOT_STOPPED = "bot.stopped"
    BOT_PAUSED = "bot.paused"
    BOT_RESUMED = "bot.resumed"
    BOT_ERROR = "bot.error"

    # Strategy events
    STRATEGY_SIGNAL = "strategy.signal"
    STRATEGY_EVALUATED = "strategy.evaluated"

    # Market events
    QUOTE_RECEIVED = "market.quote_received"
    BAR_COMPLETED = "market.bar_completed"
    SESSION_OPENED = "market.session_opened"
    SESSION_CLOSED = "market.session_closed"

    # Agent events
    AGENT_SESSION_STARTED = "agent.session_started"
    AGENT_SESSION_ENDED = "agent.session_ended"
    AGENT_TOOL_EXECUTED = "agent.tool_executed"
    AGENT_ORDER_SUBMITTED = "agent.order_submitted"

    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # Audit events
    AUDIT_LOG = "audit.log"
