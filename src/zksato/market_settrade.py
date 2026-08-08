from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from zksato.automation import AutomationEngine
from zksato.config import Settings
from zksato.domain import Quote


class SettradeRealtimeFeed:
    """Supervised Settrade v2 realtime bridge with freshness and sequence diagnostics."""

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
        self._symbols: list[str] = []
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._last_message_at: datetime | None = None
        self._last_sequence: dict[str, int] = {}
        self._gap_count = 0
        self._out_of_order_count = 0
        self._reconnect_count = 0
        self._last_error: str | None = None
        self._connected = False

    def start(self, symbols: list[str]) -> None:
        if self._task is not None and not self._task.done():
            return
        self._loop = asyncio.get_running_loop()
        self._symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._supervise())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._disconnect()

    def status(self) -> dict[str, object]:
        age: float | None = None
        if self._last_message_at is not None:
            age = max(0.0, (datetime.now(UTC) - self._last_message_at).total_seconds())
        return {
            "running": self._task is not None and not self._task.done(),
            "connected": self._connected,
            "symbols": self._symbols,
            "last_message_at": self._last_message_at.isoformat() if self._last_message_at else None,
            "last_message_age_seconds": age,
            "stale": age is None or age > self.settings.market_data_stale_seconds,
            "gap_count": self._gap_count,
            "out_of_order_count": self._out_of_order_count,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
        }

    async def _supervise(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            try:
                self._connect_once()
                self._connected = True
                self._last_error = None
                delay = 1.0
                while not self._stop.is_set() and self._connected:
                    await asyncio.sleep(min(self.settings.poll_interval_seconds, 2.0))
                    if self._last_message_at is None:
                        continue
                    age = (datetime.now(UTC) - self._last_message_at).total_seconds()
                    if age > max(self.settings.market_data_stale_seconds * 3, 30.0):
                        raise RuntimeError("Settrade realtime feed stalled; reconnecting")
            except asyncio.CancelledError:
                raise
            except (RuntimeError, OSError, ConnectionError) as exc:
                self._last_error = str(exc)
                self._connected = False
                self._disconnect()
                self._reconnect_count += 1
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
        self._disconnect()

    def _connect_once(self) -> None:
        self._disconnect()
        try:
            from settrade_v2 import Investor
        except ImportError as exc:
            raise RuntimeError("install zksato[settrade] for realtime market data") from exc
        self._investor = Investor(
            app_id=self.settings.settrade_app_id,
            app_secret=self.settings.settrade_app_secret,
            broker_id=self.settings.settrade_broker_id,
            app_code=self.settings.settrade_app_code,
            is_auto_queue=False,
        )
        self._connection = self._investor.RealtimeDataConnection()
        for symbol in self._symbols:
            price_sub = self._connection.subscribe_price_info(
                symbol=symbol,
                on_message=lambda message, item=symbol: self._on_price(item, message),
            )
            bid_sub = self._connection.subscribe_bid_offer(
                symbol=symbol,
                on_message=lambda message, item=symbol: self._on_book(item, message),
            )
            price_sub.start()
            bid_sub.start()
            self._subscriptions.extend([price_sub, bid_sub])

    def _disconnect(self) -> None:
        for subscription in self._subscriptions:
            stop = getattr(subscription, "stop", None)
            if stop is not None:
                with suppress(RuntimeError, OSError):
                    stop()
        self._subscriptions.clear()
        self._connection = None
        self._investor = None
        self._connected = False

    def _on_price(self, symbol: str, message: dict[str, Any]) -> None:
        data = self._data(message)
        if not self._accept_sequence(symbol, data):
            return
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
            open=self._number(data, "open"),
            previous_close=previous_close,
            volume=self._number(data, "totalVolume", "total_volume") or 0,
            value=self._number(data, "totalValue", "total_value") or 0,
            timestamp=self._timestamp(data),
        )
        self._last_message_at = datetime.now(UTC)
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
            self._last_message_at = datetime.now(UTC)

    def _accept_sequence(self, symbol: str, data: dict[str, Any]) -> bool:
        raw = data.get("sequence", data.get("seq", data.get("sequenceNo")))
        if raw is None:
            return True
        try:
            sequence = int(raw)
        except (TypeError, ValueError):
            return True
        previous = self._last_sequence.get(symbol)
        if previous is not None:
            if sequence <= previous:
                self._out_of_order_count += 1
                return False
            if sequence > previous + 1:
                self._gap_count += sequence - previous - 1
        self._last_sequence[symbol] = sequence
        return True

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

    @staticmethod
    def _timestamp(data: dict[str, Any]) -> datetime:
        raw = data.get("timestamp", data.get("time"))
        if isinstance(raw, datetime):
            return raw.astimezone(UTC) if raw.tzinfo else raw.replace(tzinfo=UTC)
        if isinstance(raw, (int, float)):
            seconds = float(raw)
            if seconds > 10_000_000_000:
                seconds /= 1000
            try:
                return datetime.fromtimestamp(seconds, UTC)
            except (ValueError, OSError, OverflowError):
                pass
        if isinstance(raw, str):
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                pass
        return datetime.now(UTC)
