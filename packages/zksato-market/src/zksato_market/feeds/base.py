"""Feed protocol and base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncGenerator, Callable, Generic, TypeVar

from zksato_market.types import FeedEvent, FeedStatus, MarketType
from zksato_core.models import Quote, Trade, Bar
from zksato_core.exceptions import MarketDataError


T = TypeVar("T")


@dataclass
class FeedMetrics:
    """Feed metrics."""

    messages_received: int = 0
    messages_processed: int = 0
    errors: int = 0
    last_message_at: datetime | None = None
    latency_ms: float = 0.0


class Feed(ABC, Generic[T]):
    """Base feed class."""

    def __init__(self, name: str, market_type: MarketType) -> None:
        self.name = name
        self.market_type = market_type
        self._status = FeedStatus.DISCONNECTED
        self._metrics = FeedMetrics()
        self._handlers: list[Callable[[T], None]] = []

    @property
    def status(self) -> FeedStatus:
        return self._status

    @property
    def metrics(self) -> FeedMetrics:
        return self._metrics

    def add_handler(self, handler: Callable[[T], None]) -> None:
        """Add a message handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[T], None]) -> bool:
        """Remove a message handler."""
        try:
            self._handlers.remove(handler)
            return True
        except ValueError:
            return False

    def _emit(self, data: T) -> None:
        """Emit data to handlers."""
        self._metrics.messages_received += 1
        self._metrics.last_message_at = datetime.now()
        for handler in self._handlers:
            try:
                handler(data)
                self._metrics.messages_processed += 1
            except Exception:
                self._metrics.errors += 1

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the feed."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the feed."""
        ...

    @abstractmethod
    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols."""
        ...

    @abstractmethod
    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols."""
        ...


class MarketDataFeed(Feed[FeedEvent]):
    """Market data feed with typed events."""

    def __init__(self, name: str, market_type: MarketType) -> None:
        super().__init__(name, market_type)
        self._quote_handlers: list[Callable[[Quote], None]] = []
        self._trade_handlers: list[Callable[[Trade], None]] = []
        self._bar_handlers: list[Callable[[Bar], None]] = []

    def add_quote_handler(self, handler: Callable[[Quote], None]) -> None:
        self._quote_handlers.append(handler)

    def add_trade_handler(self, handler: Callable[[Trade], None]) -> None:
        self._trade_handlers.append(handler)

    def add_bar_handler(self, handler: Callable[[Bar], None]) -> None:
        self._bar_handlers.append(handler)

    def _emit_quote(self, quote: Quote) -> None:
        self._metrics.messages_received += 1
        self._metrics.last_message_at = datetime.now()
        for handler in self._quote_handlers:
            try:
                handler(quote)
                self._metrics.messages_processed += 1
            except Exception:
                self._metrics.errors += 1

    def _emit_trade(self, trade: Trade) -> None:
        for handler in self._trade_handlers:
            try:
                handler(trade)
            except Exception:
                self._metrics.errors += 1

    def _emit_bar(self, bar: Bar) -> None:
        for handler in self._bar_handlers:
            try:
                handler(bar)
            except Exception:
                self._metrics.errors += 1


class CompositeFeed(MarketDataFeed):
    """Composite feed with primary and fallback feeds."""

    def __init__(
        self,
        name: str,
        market_type: MarketType,
        primary: MarketDataFeed,
        fallback: MarketDataFeed | None = None,
    ) -> None:
        super().__init__(name, market_type)
        self.primary = primary
        self.fallback = fallback
        self._use_fallback = False

    async def connect(self) -> None:
        await self.primary.connect()
        if self.fallback:
            await self.fallback.connect()
        self._status = FeedStatus.CONNECTED

    async def disconnect(self) -> None:
        await self.primary.disconnect()
        if self.fallback:
            await self.fallback.disconnect()
        self._status = FeedStatus.DISCONNECTED

    async def subscribe(self, symbols: list[str]) -> None:
        await self.primary.subscribe(symbols)
        if self.fallback:
            await self.fallback.subscribe(symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        await self.primary.unsubscribe(symbols)
        if self.fallback:
            await self.fallback.unsubscribe(symbols)

    def _emit_quote(self, quote: Quote) -> None:
        if not self._use_fallback:
            super()._emit_quote(quote)
        elif self.fallback:
            self.fallback._emit_quote(quote)

    def _emit_trade(self, trade: Trade) -> None:
        if not self._use_fallback:
            super()._emit_trade(trade)
        elif self.fallback:
            self.fallback._emit_trade(trade)

    def _emit_bar(self, bar: Bar) -> None:
        if not self._use_fallback:
            super()._emit_bar(bar)
        elif self.fallback:
            self.fallback._emit_bar(bar)

    def switch_to_fallback(self) -> bool:
        """Switch to fallback feed."""
        if self.fallback and not self._use_fallback:
            self._use_fallback = True
            return True
        return False

    def switch_to_primary(self) -> bool:
        """Switch back to primary feed."""
        if self._use_fallback:
            self._use_fallback = False
            return True
        return False