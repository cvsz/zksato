from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from zksato.automation import AutomationEngine
from zksato.config import Settings
from zksato.domain import Quote


class SettradeRealtimeFeed:
    """Settrade v2 realtime price/bid-offer subscriptions bridged into asyncio."""

    def __init__(self, settings: Settings, automation: AutomationEngine) -> None:
        if not settings.settrade_configured:
            raise RuntimeError("Settrade credentials are incomplete")
        self.settings = settings
        self.automation = automation
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscriptions: list[Any] = []
        self._books: dict[str, dict[str, float]] = {}
        self._investor: Any = None
        self._connection: Any = None

    def start(self, symbols: list[str]) -> None:
        if self._subscriptions:
            return
        try:
            from settrade_v2 import Investor  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("install zksato[settrade] for realtime market data") from exc
        self._loop = asyncio.get_running_loop()
        self._investor = Investor(
            app_id=self.settings.settrade_app_id,
            app_secret=self.settings.settrade_app_secret,
            broker_id=self.settings.settrade_broker_id,
            app_code=self.settings.settrade_app_code,
            is_auto_queue=False,
        )
        self._connection = self._investor.RealtimeDataConnection()
        for symbol in symbols:
            normalized = symbol.upper()
            price_sub = self._connection.subscribe_price_info(
                symbol=normalized,
                on_message=lambda message, item=normalized: self._on_price(item, message),
            )
            bid_sub = self._connection.subscribe_bid_offer(
                symbol=normalized,
                on_message=lambda message, item=normalized: self._on_book(item, message),
            )
            price_sub.start()
            bid_sub.start()
            self._subscriptions.extend([price_sub, bid_sub])

    def stop(self) -> None:
        for subscription in self._subscriptions:
            stop = getattr(subscription, "stop", None)
            if stop is not None:
                stop()
        self._subscriptions.clear()

    def _on_price(self, symbol: str, message: dict[str, Any]) -> None:
        data = self._data(message)
        last = self._number(data, "last", "lastPrice")
        if not last or last <= 0:
            return
        change = self._number(data, "change") or 0.0
        book = self._books.get(symbol, {})
        previous_close = last - change if last - change > 0 else None
        quote = Quote(
            symbol=symbol,
            last=last,
            bid=book.get("bid"),
            offer=book.get("offer"),
            high=self._number(data, "high"),
            low=self._number(data, "low"),
            previous_close=previous_close,
            volume=self._number(data, "totalVolume", "total_volume") or 0,
            value=self._number(data, "totalValue", "total_value") or 0,
            timestamp=datetime.now(UTC),
        )
        self._schedule(quote)

    def _on_book(self, symbol: str, message: dict[str, Any]) -> None:
        data = self._data(message)
        bid = self._number(data, "bid", "bidPrice1", "bestBid")
        offer = self._number(data, "offer", "offerPrice1", "bestOffer")
        if bid or offer:
            self._books[symbol] = {
                key: value
                for key, value in {"bid": bid, "offer": offer}.items()
                if value and value > 0
            }

    def _schedule(self, quote: Quote) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.automation.on_quote(quote), loop)

    @staticmethod
    def _data(message: dict[str, Any]) -> dict[str, Any]:
        nested = message.get("data")
        return nested if isinstance(nested, dict) else message

    @staticmethod
    def _number(data: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None
