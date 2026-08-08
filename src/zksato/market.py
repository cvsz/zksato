from __future__ import annotations

import asyncio
import random
from contextlib import suppress
from datetime import UTC, datetime

from zksato.automation import AutomationEngine
from zksato.domain import Quote


class DemoMarketFeed:
    """Synthetic feed for local demos and CI; never represents real market data."""

    DEFAULTS = {
        "AOT": 42.50,
        "PTT": 31.25,
        "CPALL": 58.00,
        "KBANK": 132.50,
        "ADVANC": 218.00,
    }

    def __init__(self, automation: AutomationEngine) -> None:
        self.automation = automation
        self.running = False
        self._task: asyncio.Task[None] | None = None
        self._prices = dict(self.DEFAULTS)

    def start(self, symbols: list[str]) -> None:
        if self.running:
            return
        for symbol in symbols:
            self._prices.setdefault(symbol, 100.0)
        self.running = True
        self._task = asyncio.create_task(self._run(symbols))

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self, symbols: list[str]) -> None:
        while self.running:
            for symbol in symbols:
                previous = self._prices[symbol]
                move = random.uniform(-0.006, 0.006)
                last = max(0.01, round(previous * (1 + move), 2))
                self._prices[symbol] = last
                spread = max(0.01, round(last * 0.0005, 2))
                await self.automation.on_quote(
                    Quote(
                        symbol=symbol,
                        last=last,
                        bid=max(0.01, round(last - spread, 2)),
                        offer=round(last + spread, 2),
                        high=max(previous, last),
                        low=min(previous, last),
                        open=previous,
                        previous_close=previous,
                        volume=random.randint(1_000, 100_000),
                        value=random.randint(100_000, 10_000_000),
                        timestamp=datetime.now(UTC),
                    )
                )
            await asyncio.sleep(1)
