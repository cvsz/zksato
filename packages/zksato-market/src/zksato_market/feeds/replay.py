"""Deterministic replay feed."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime

from zksato_core.models import Bar, Quote, Trade

from zksato_market.feeds.base import MarketDataFeed
from zksato_market.types import FeedStatus, MarketType


@dataclass
class ReplayEvent:
    """Event for replay."""

    timestamp: datetime
    event_type: str  # "quote", "trade", "bar"
    data: Quote | Trade | Bar


class ReplayFeed(MarketDataFeed):
    """Deterministic replay feed for backtesting."""

    def __init__(
        self,
        name: str,
        market_type: MarketType,
        events: list[ReplayEvent] | None = None,
        speed: float = 1.0,
    ) -> None:
        super().__init__(name, market_type)
        self.events = events or []
        self.speed = speed
        self._current_idx = 0
        self._running = False
        self._task = None

    def add_event(self, event: ReplayEvent) -> None:
        """Add an event to replay."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def add_quote(self, timestamp: datetime, quote: Quote) -> None:
        """Add a quote event."""
        self.add_event(ReplayEvent(timestamp, "quote", quote))

    def add_trade(self, timestamp: datetime, trade: Trade) -> None:
        """Add a trade event."""
        self.add_event(ReplayEvent(timestamp, "trade", trade))

    def add_bar(self, timestamp: datetime, bar: Bar) -> None:
        """Add a bar event."""
        self.add_event(ReplayEvent(timestamp, "bar", bar))

    async def connect(self) -> None:
        """Connect to replay feed."""
        self._status = FeedStatus.CONNECTED
        self._current_idx = 0
        self._running = True

    async def disconnect(self) -> None:
        """Disconnect from replay feed."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._status = FeedStatus.DISCONNECTED

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols (no-op for replay)."""
        pass

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols (no-op for replay)."""
        pass

    async def start_replay(self) -> None:
        """Start replaying events."""
        self._task = asyncio.create_task(self._replay_loop())

    async def _replay_loop(self) -> None:
        """Main replay loop."""
        last_timestamp = None

        while self._running and self._current_idx < len(self.events):
            event = self.events[self._current_idx]

            # Calculate delay based on timestamp difference
            if last_timestamp is not None:
                delay = (event.timestamp - last_timestamp).total_seconds() / self.speed
                if delay > 0:
                    await asyncio.sleep(delay)

            # Emit event
            if event.event_type == "quote":
                self._emit_quote(event.data)
            elif event.event_type == "trade":
                self._emit_trade(event.data)
            elif event.event_type == "bar":
                self._emit_bar(event.data)

            last_timestamp = event.timestamp
            self._current_idx += 1

        self._running = False

    def pause(self) -> None:
        """Pause replay."""
        self._running = False

    def resume(self) -> None:
        """Resume replay."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._replay_loop())

    def seek(self, timestamp: datetime) -> None:
        """Seek to a specific timestamp."""
        # Find the first event at or after the timestamp
        for i, event in enumerate(self.events):
            if event.timestamp >= timestamp:
                self._current_idx = i
                break

    def reset(self) -> None:
        """Reset to beginning."""
        self._current_idx = 0
