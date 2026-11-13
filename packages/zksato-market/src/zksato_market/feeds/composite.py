"""Multi-feed with fallback."""

from __future__ import annotations

import contextlib

from zksato_core.datetime import now_utc
from zksato_core.models import Bar, Quote, Trade

from zksato_market.feeds.base import MarketDataFeed
from zksato_market.types import MarketType


class MultiFeed(MarketDataFeed):
    """Multi-source feed with automatic fallback."""

    def __init__(
        self,
        name: str,
        market_type: MarketType,
        feeds: list[MarketDataFeed],
        health_check_interval: float = 30.0,
    ) -> None:
        super().__init__(name, market_type)
        self.feeds = feeds
        self.health_check_interval = health_check_interval
        self._current_feed_idx = 0
        self._health_check_task = None

    @property
    def current_feed(self) -> MarketDataFeed:
        return self.feeds[self._current_feed_idx]

    async def connect(self) -> None:
        """Connect all feeds."""
        for feed in self.feeds:
            # A single unhealthy feed must not block the composite
            with contextlib.suppress(Exception):
                await feed.connect()

        # Find first connected feed
        for i, feed in enumerate(self.feeds):
            if feed.status == feed.status.__class__.CONNECTED:
                self._current_feed_idx = i
                break

        self._status = self._status.__class__.CONNECTED

        # Start health check
        # self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def disconnect(self) -> None:
        """Disconnect all feeds."""
        # if self._health_check_task:
        #     self._health_check_task.cancel()
        for feed in self.feeds:
            with contextlib.suppress(Exception):
                await feed.disconnect()
        self._status = self._status.__class__.DISCONNECTED

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols on all feeds."""
        for feed in self.feeds:
            with contextlib.suppress(Exception):
                await feed.subscribe(symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols on all feeds."""
        for feed in self.feeds:
            with contextlib.suppress(Exception):
                await feed.unsubscribe(symbols)

    def _emit_quote(self, quote: Quote) -> None:
        super()._emit_quote(quote)
        # Also emit to current feed for metrics
        self.current_feed._emit_quote(quote)

    def _emit_trade(self, trade: Trade) -> None:
        super()._emit_trade(trade)
        self.current_feed._emit_trade(trade)

    def _emit_bar(self, bar: Bar) -> None:
        super()._emit_bar(bar)
        self.current_feed._emit_bar(bar)

    async def _health_check_loop(self) -> None:
        """Periodic health check with fallback."""
        import asyncio

        while True:
            await asyncio.sleep(self.health_check_interval)
            await self._check_and_failover()

    async def _check_and_failover(self) -> None:
        """Check feed health and failover if needed."""
        current = self.current_feed

        # Check if current feed is healthy
        if current.metrics.last_message_at:
            from zksato_core.datetime import now_utc

            age = (now_utc() - current.metrics.last_message_at).total_seconds()
            if age > self.health_check_interval * 2:
                # Try to failover
                await self._failover()

    async def _failover(self) -> None:
        """Failover to next healthy feed."""
        for i in range(1, len(self.feeds)):
            next_idx = (self._current_feed_idx + i) % len(self.feeds)
            feed = self.feeds[next_idx]

            # Check if feed is receiving data
            if feed.status == feed.status.__class__.CONNECTED and feed.metrics.last_message_at:
                age = (now_utc() - feed.metrics.last_message_at).total_seconds()
                if age < self.health_check_interval * 2:
                    self._current_feed_idx = next_idx
                    return
        # No healthy feed found
        pass


class FeedRouter:
    """Feed router with priority-based failover (alias for MultiFeed)."""

    def __init__(
        self,
        feeds: list[MarketDataFeed],
        strategy: str = "priority",
    ) -> None:
        # Use first feed's name and market type
        name = f"router_{feeds[0].name}" if feeds else "router"
        market_type = feeds[0].market_type if feeds else MarketType.EQUITY
        self.multi_feed = MultiFeed(name, market_type, feeds)

    @property
    def name(self) -> str:
        return self.multi_feed.name

    @property
    def market_type(self) -> MarketType:
        return self.multi_feed.market_type

    @property
    def status(self):
        return self.multi_feed.status

    @property
    def metrics(self):
        return self.multi_feed.metrics

    async def connect(self) -> None:
        await self.multi_feed.connect()

    async def disconnect(self) -> None:
        await self.multi_feed.disconnect()

    async def subscribe(self, symbols: list[str]) -> None:
        await self.multi_feed.subscribe(symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        await self.multi_feed.unsubscribe(symbols)

    @property
    def active_feed(self) -> MarketDataFeed:
        return self.multi_feed.current_feed
