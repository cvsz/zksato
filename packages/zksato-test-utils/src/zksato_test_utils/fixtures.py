"""Test fixtures for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from zksato_core.types import OrderType, OrderStatus, Side
from zksato_core.models import OrderRecord, Quote, PortfolioSnapshot, Position
from zksato_broker.protocol import BrokerAdapter


@dataclass
class MockBroker:
    """Mock broker for testing."""
    
    def __init__(self):
        self.orders: list[OrderRecord] = []
        self.positions: dict[str, Position] = {}
        self.cash = 500_000.0
        self._connected = True
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def capabilities(self) -> set[str]:
        return {"paper_trading", "equity", "market_orders", "limit_orders"}
    
    async def connect(self, config: Any = None) -> None:
        self._connected = True
    
    async def disconnect(self) -> None:
        self._connected = False
    
    async def place_order(self, order: Any) -> OrderRecord:
        record = OrderRecord(
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            price=order.price,
            status=OrderStatus.FILLED,
            source="mock",
        )
        self.orders.append(record)
        return record
    
    async def cancel_order(self, order_id: str) -> OrderRecord:
        order = next((o for o in self.orders if str(o.id) == order_id), None)
        if order:
            order.status = OrderStatus.CANCELLED
            return order
        raise ValueError("Order not found")
    
    async def list_orders(self, status: OrderStatus | None = None) -> list[OrderRecord]:
        if status:
            return [o for o in self.orders if o.status == status]
        return self.orders
    
    async def get_positions(self) -> list[Position]:
        return list(self.positions.values())
    
    async def get_account(self) -> dict[str, Any]:
        return {"cash": self.cash, "equity": self.cash}
    
    async def get_portfolio(self) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            cash=self.cash,
            market_value=sum(p.market_value for p in self.positions.values()),
            equity=self.cash,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            daily_pnl=0.0,
            positions=list(self.positions.values()),
        )
    
    async def health_check(self) -> dict[str, Any]:
        return {"status": "healthy", "broker": "mock"}
    
    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        return {"symbol": symbol, "bid": 100.0, "ask": 100.5, "last": 100.25}


@pytest.fixture
def mock_broker() -> MockBroker:
    """Provide a mock broker for testing."""
    return MockBroker()


@pytest.fixture
def mock_market_feed():
    """Provide a mock market feed for testing."""
    feed = MagicMock()
    feed.name = "mock_feed"
    feed.connect = AsyncMock()
    feed.disconnect = AsyncMock()
    feed.get_quote = AsyncMock(return_value=Quote(
        symbol="TEST",
        bid=100.0,
        ask=100.5,
        last=100.25,
        timestamp=datetime.now(UTC),
    ))
    feed.subscribe = AsyncMock()
    feed.unsubscribe = AsyncMock()
    return feed