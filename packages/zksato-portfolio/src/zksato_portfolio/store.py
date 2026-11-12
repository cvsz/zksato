"""State store for zksato."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from zksato_core.models import Quote, OrderRecord, OrderEvent, OrderStatus
from zksato_portfolio.persistence import PersistenceLayer, InMemoryPersistence


class StateStore:
    """State store for orders, quotes, and events."""
    
    def __init__(self, persistence: PersistenceLayer | None = None) -> None:
        self.persistence = persistence or InMemoryPersistence()
        self._quotes: dict[str, Quote] = {}
    
    async def upsert_order(self, order: OrderRecord) -> None:
        await self.persistence.save_order(order)
    
    async def get_order(self, order_id: str) -> OrderRecord | None:
        return await self.persistence.get_order(order_id)
    
    async def list_orders(self) -> list[OrderRecord]:
        return await self.persistence.list_orders()
    
    async def list_orders_by_status(self, status: OrderStatus) -> list[OrderRecord]:
        return await self.persistence.list_orders(status.value)
    
    async def add_order_event(self, event: OrderEvent) -> None:
        await self.persistence.save_order_event(event)
    
    async def get_order_events(self, order_id: str) -> list[OrderEvent]:
        return await self.persistence.get_order_events(order_id)
    
    async def record_order_fill(self, order: OrderRecord, source: str) -> None:
        from zksato_core.models import FillRecord
        fill = FillRecord(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.filled_quantity,
            price=order.average_fill_price or 0.0,
            source=source,
            timestamp=datetime.now(UTC),
        )
        await self.persistence.save_fill(fill)
    
    def get_quote(self, symbol: str) -> Quote | None:
        return self._quotes.get(symbol)
    
    def upsert_quote(self, quote: Quote) -> None:
        self._quotes[quote.symbol] = quote
    
    def add_audit(self, event_type: str, message: str, data: dict[str, Any] | None = None) -> None:
        from zksato_core.models import AuditEvent
        audit = AuditEvent(
            event_type=event_type,
            message=message,
            data=data or {},
            timestamp=datetime.now(UTC),
        )
        self.persistence.save_audit(audit)
    
    async def get_pending_outbox(self, limit: int = 100) -> list[Any]:
        return await self.persistence.get_pending_outbox(limit)
    
    async def mark_outbox_sent(self, message_id: str) -> None:
        await self.persistence.mark_outbox_sent(message_id)