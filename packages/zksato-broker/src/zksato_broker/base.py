"""Base broker adapter class with common functionality."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from zksato_core.types import Side, OrderType, OrderStatus
from zksato_core.models import OrderIntent, OrderRecord, PortfolioSnapshot, Position
from zksato_broker.protocol import BrokerAdapter, BrokerConfig, BrokerCapabilities


class BrokerError(Exception):
    """Base exception for broker errors."""
    
    def __init__(
        self,
        message: str,
        category: str = "unknown",
        original_error: Exception | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.original_error = original_error
        self.retry_after = retry_after


class BrokerConnectionError(BrokerError):
    """Broker connection error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, category="connection", original_error=original_error)


class BrokerAuthenticationError(BrokerError):
    """Broker authentication error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, category="authentication", original_error=original_error)


class BrokerRateLimitError(BrokerError):
    """Broker rate limit error."""
    def __init__(self, message: str, retry_after: float | None = None, original_error: Exception | None = None) -> None:
        super().__init__(message, category="rate_limit", original_error=original_error, retry_after=retry_after)


class BrokerInvalidOrderError(BrokerError):
    """Invalid order error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, category="invalid_order", original_error=original_error)


class BrokerRejectedError(BrokerError):
    """Order rejected by broker."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, category="rejected", original_error=original_error)


class BrokerUnknownError(BrokerError):
    """Unknown broker error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, category="unknown", original_error=original_error)


class BrokerAmbiguousError(RuntimeError):
    """The broker request may have been accepted but the response is unknown."""
    pass


class BaseBroker(ABC):
    """Base class for broker adapters with common functionality."""
    
    def __init__(self, config: BrokerConfig) -> None:
        self.config = config
        self._connected = False
        self._lock = asyncio.Lock()
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def capabilities(self) -> set[BrokerCapabilities]:
        return self.config.capabilities
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self, config: BrokerConfig | None = None) -> None:
        """Connect to the broker."""
        if config:
            self.config = config
        async with self._lock:
            if self._connected:
                return
            await self._do_connect()
            self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        async with self._lock:
            if not self._connected:
                return
            await self._do_disconnect()
            self._connected = False
    
    @abstractmethod
    async def _do_connect(self) -> None:
        """Implement broker-specific connection logic."""
        ...
    
    @abstractmethod
    async def _do_disconnect(self) -> None:
        """Implement broker-specific disconnection logic."""
        ...
    
    @abstractmethod
    async def place_order(self, order: OrderIntent) -> OrderRecord:
        """Place an order."""
        ...
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderRecord:
        """Cancel an order."""
        ...
    
    async def get_order(self, order_id: str) -> OrderRecord | None:
        """Get order by ID. Default implementation searches list_orders."""
        orders = await self.list_orders()
        for order in orders:
            if str(getattr(order, 'id', '')) == order_id or \
               str(getattr(order, 'broker_order_id', '')) == order_id or \
               str(getattr(order, 'client_order_id', '')) == order_id:
                return order
        return None
    
    @abstractmethod
    async def list_orders(self, status: OrderStatus | None = None) -> list[OrderRecord]:
        """List orders."""
        ...
    
    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get current positions."""
        ...
    
    @abstractmethod
    async def get_account(self) -> dict[str, Any]:
        """Get account information."""
        ...
    
    @abstractmethod
    async def get_portfolio(self) -> PortfolioSnapshot:
        """Get portfolio snapshot."""
        ...
    
    async def health_check(self) -> dict[str, Any]:
        """Check broker health status."""
        try:
            await self.get_account()
            return {"status": "healthy", "broker": self.name, "connected": self._connected}
        except Exception as e:
            return {"status": "unhealthy", "broker": self.name, "connected": self._connected, "error": str(e)}
    
    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        """Get current quote for a symbol. Override in subclasses."""
        return None
    
    def _create_order_record(
        self,
        intent: OrderIntent,
        broker_order_id: str | None = None,
        status: OrderStatus = OrderStatus.ACCEPTED,
        filled_quantity: float = 0.0,
        average_fill_price: float | None = None,
        message: str | None = None,
    ) -> OrderRecord:
        """Create an OrderRecord from an OrderIntent."""
        now = datetime.now(UTC)
        return OrderRecord(
            broker_order_id=broker_order_id,
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            filled_quantity=filled_quantity,
            order_type=intent.order_type,
            price=intent.price,
            average_fill_price=average_fill_price,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            status=status,
            source=intent.source or self.name,
            message=message,
            created_at=now,
            updated_at=now,
        )
    
    def _classify_error(self, error: Exception) -> BrokerError:
        """Classify an exception into a BrokerError."""
        from zksato_broker.errors import classify_error
        return classify_error(error, self.name)