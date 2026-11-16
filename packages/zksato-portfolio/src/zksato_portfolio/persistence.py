"""Persistence layer for zksato."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from zksato_core.models import AuditEvent, FillRecord, OrderEvent, OrderRecord, OutboxMessage


class PersistenceLayer(ABC):
    """Abstract persistence layer."""

    @abstractmethod
    async def save_order(self, order: OrderRecord) -> None: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> OrderRecord | None: ...

    @abstractmethod
    async def list_orders(self, status: str | None = None) -> list[OrderRecord]: ...

    @abstractmethod
    async def save_order_event(self, event: OrderEvent) -> None: ...

    @abstractmethod
    async def get_order_events(self, order_id: str) -> list[OrderEvent]: ...

    @abstractmethod
    async def save_fill(self, fill: FillRecord) -> None: ...

    @abstractmethod
    async def get_fills(self, order_id: str | None = None) -> list[FillRecord]: ...

    @abstractmethod
    async def save_audit(self, audit: AuditEvent) -> None: ...

    @abstractmethod
    async def get_audits(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> list[AuditEvent]: ...

    @abstractmethod
    async def save_outbox(self, message: OutboxMessage) -> None: ...

    @abstractmethod
    async def get_pending_outbox(self, limit: int = 100) -> list[OutboxMessage]: ...

    @abstractmethod
    async def mark_outbox_sent(self, message_id: str) -> None: ...

    @abstractmethod
    async def mark_outbox_dead_lettered(self, message_id: str) -> None: ...


class InMemoryPersistence(PersistenceLayer):
    """In-memory persistence for testing."""

    def __init__(self) -> None:
        self._orders: dict[str, OrderRecord] = {}
        self._order_events: dict[str, list[OrderEvent]] = {}
        self._fills: list[FillRecord] = []
        self._audits: list[AuditEvent] = []
        self._outbox: list[OutboxMessage] = []

    async def save_order(self, order: OrderRecord) -> None:
        self._orders[str(order.id)] = order

    async def get_order(self, order_id: str) -> OrderRecord | None:
        return self._orders.get(order_id)

    async def list_orders(self, status: str | None = None) -> list[OrderRecord]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status.value == status]
        return orders

    async def save_order_event(self, event: OrderEvent) -> None:
        if str(event.order_id) not in self._order_events:
            self._order_events[str(event.order_id)] = []
        self._order_events[str(event.order_id)].append(event)

    async def get_order_events(self, order_id: str) -> list[OrderEvent]:
        return self._order_events.get(order_id, [])

    async def save_fill(self, fill: FillRecord) -> None:
        self._fills.append(fill)

    async def get_fills(self, order_id: str | None = None) -> list[FillRecord]:
        if order_id:
            return [f for f in self._fills if f.order_id == order_id]
        return self._fills

    async def save_audit(self, audit: AuditEvent) -> None:
        self._audits.append(audit)

    async def get_audits(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> list[AuditEvent]:
        audits = self._audits
        if start:
            audits = [a for a in audits if a.timestamp >= start]
        if end:
            audits = [a for a in audits if a.timestamp <= end]
        return audits

    async def save_outbox(self, message: OutboxMessage) -> None:
        self._outbox.append(message)

    async def get_pending_outbox(self, limit: int = 100) -> list[OutboxMessage]:
        pending = [m for m in self._outbox if not m.sent_at and not m.dead_lettered_at]
        return pending[:limit]

    async def mark_outbox_sent(self, message_id: str) -> None:
        for m in self._outbox:
            if str(m.id) == message_id:
                m.sent_at = datetime.now(UTC)
                break

    async def mark_outbox_dead_lettered(self, message_id: str) -> None:
        for m in self._outbox:
            if str(m.id) == message_id:
                m.dead_lettered_at = datetime.now(UTC)
                break
