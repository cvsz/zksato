"""Broker adapter protocol and capabilities for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from zksato_core.models import OrderIntent, OrderRecord, PortfolioSnapshot
from zksato_core.types import OrderStatus


class BrokerCapabilities(str, Enum):
    """Capabilities that a broker may support."""

    EQUITY = "equity"
    TFEX_FUTURES = "tfex_futures"
    TFEX_OPTIONS = "tfex_options"
    CRYPTO_SPOT = "crypto_spot"
    CRYPTO_FUTURES = "crypto_futures"
    PREDICTION_MARKETS = "prediction_markets"
    PAPER_TRADING = "paper_trading"
    MARKET_ORDERS = "market_orders"
    LIMIT_ORDERS = "limit_orders"
    STOP_ORDERS = "stop_orders"
    STOP_LIMIT_ORDERS = "stop_limit_orders"
    OCO_ORDERS = "oco_orders"
    BRACKET_ORDERS = "bracket_orders"
    FRACTIONAL_SHARES = "fractional_shares"
    SHORT_SELLING = "short_selling"
    MARGIN_TRADING = "margin_trading"
    REALTIME_QUOTES = "realtime_quotes"
    HISTORICAL_DATA = "historical_data"
    ORDER_HISTORY = "order_history"
    POSITION_TRACKING = "position_tracking"
    ACCOUNT_BALANCE = "account_balance"
    WEBSOCKET_STREAMS = "websocket_streams"
    SANDBOX_MODE = "sandbox_mode"


@dataclass
class BrokerConfig:
    """Configuration for a broker adapter."""

    name: str
    capabilities: set[BrokerCapabilities]
    trading_mode: str = "paper"
    sandbox: bool = False
    credentials: dict[str, str] | None = None
    extra: dict[str, str] | None = None


@runtime_checkable
class BrokerAdapter(Protocol):
    """Protocol for broker adapters.

    All broker implementations must conform to this protocol.
    """

    @property
    def name(self) -> str:
        """Unique name of the broker."""
        ...

    @property
    def capabilities(self) -> set[BrokerCapabilities]:
        """Set of capabilities this broker supports."""
        ...

    async def connect(self, config: BrokerConfig) -> None:
        """Connect to the broker with given configuration."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        ...

    async def place_order(self, order: OrderIntent) -> OrderRecord:
        """Place an order and return the order record."""
        ...

    async def cancel_order(self, order_id: str) -> OrderRecord:
        """Cancel an order by ID."""
        ...

    async def get_order(self, order_id: str) -> OrderRecord | None:
        """Get order by ID."""
        ...

    async def list_orders(self, status: OrderStatus | None = None) -> list[OrderRecord]:
        """List orders, optionally filtered by status."""
        ...

    async def get_positions(self) -> list:
        """Get current positions."""
        ...

    async def get_account(self) -> dict:
        """Get account information."""
        ...

    async def get_portfolio(self) -> PortfolioSnapshot:
        """Get portfolio snapshot."""
        ...

    async def health_check(self) -> dict:
        """Check broker health status."""
        ...

    async def get_quote(self, symbol: str) -> dict | None:
        """Get current quote for a symbol."""
        ...
