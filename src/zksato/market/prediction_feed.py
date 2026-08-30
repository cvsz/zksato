from __future__ import annotations

import asyncio
import json
import logging
import math
import random
from collections import deque
from contextlib import suppress
from datetime import UTC, datetime
from typing import Callable

import httpx

from zksato.config import Settings
from zksato.domain import Quote
from zksato.market.ccxt_feed import _BINANCE_SYMBOL_MAP, _KUCOIN_SYMBOL_MAP
from zksato.prediction.core import Tick

logger = logging.getLogger(__name__)

_CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL"}


class PredictionMarketFeed:
    """Synthetic prediction-market tick feed backed by crypto spot references.

    Ingests reference prices from configured CCXT exchanges and generates
    UP/DOWN tick data. Falls back to a deterministic synthetic generator when
    external feeds are unavailable. Fails closed for automated execution if
    the tick stream becomes stale.
    """

    def __init__(
        self,
        settings: Settings,
        reference_callback: Callable[[str, float], None] | None = None,
    ) -> None:
        self.settings = settings
        self._reference_callback = reference_callback
        self.running = False
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._symbols: list[str] = []
        self._http: httpx.AsyncClient | None = None
        self._last_tick_at: datetime | None = None
        self._last_reference_at: datetime | None = None
        self._reconnect_count = 0
        self._last_error: str | None = None
        self._ticks: dict[str, deque[Tick]] = {}
        self._spot_history: dict[str, deque[float]] = {}
        self._rng = random.Random(42)
        self._max_history = 64

    def start(self, symbols: list[str]) -> None:
        if self.running:
            return
        self._symbols = sorted({s.strip().upper() for s in symbols if s.strip()})
        for symbol in self._symbols:
            self._ticks[symbol] = deque(maxlen=1000)
            self._spot_history[symbol] = deque(maxlen=self._max_history)
        self.running = True
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.running = False
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def status(self) -> dict[str, object]:
        age: float | None = None
        if self._last_tick_at is not None:
            age = max(0.0, (datetime.now(UTC) - self._last_tick_at).total_seconds())
        return {
            "running": self.running,
            "symbols": self._symbols,
            "last_tick_at": self._last_tick_at.isoformat() if self._last_tick_at else None,
            "last_tick_age_seconds": age,
            "stale": age is None or age > self.settings.market_data_stale_seconds,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
        }

    def get_ticks(self, symbol: str, limit: int = 100) -> list[Tick]:
        symbol = symbol.strip().upper()
        ticks = self._ticks.get(symbol, deque(maxlen=1000))
        return list(ticks)[-limit:]

    async def on_reference_quote(self, quote: Quote) -> None:
        symbol = quote.symbol.strip().upper()
        if symbol not in self._symbols:
            return
        self._last_reference_at = datetime.now(UTC)
        if self._reference_callback is not None:
            self._reference_callback(symbol, quote.last)
        history = self._spot_history.setdefault(symbol, deque(maxlen=self._max_history))
        history.append(quote.last)

    async def _run(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            try:
                if self._http is None:
                    self._http = httpx.AsyncClient(timeout=10.0)
                if self.settings.ccxt_configured:
                    await self._refresh_reference_prices()
                self._last_error = None
                delay = 1.0
                while not self._stop.is_set():
                    await asyncio.sleep(min(self.settings.poll_interval_seconds, 2.0))
                    for symbol in self._symbols:
                        await self._generate_tick(symbol)
                    if self._last_tick_at is not None:
                        age = (datetime.now(UTC) - self._last_tick_at).total_seconds()
                        if age > max(self.settings.market_data_stale_seconds * 3, 30.0):
                            raise RuntimeError("prediction feed stalled; reconnecting")
            except asyncio.CancelledError:
                raise
            except (RuntimeError, OSError, ConnectionError) as exc:
                self._last_error = str(exc)
                self._reconnect_count += 1
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
            finally:
                if self._http is not None:
                    await self._http.aclose()
                    self._http = None
        self._last_error = None

    async def _refresh_reference_prices(self) -> None:
        if self._http is None:
            return
        for exchange_id in self.settings.ccxt_exchange_list:
            for symbol in self._symbols:
                if symbol not in _CRYPTO_SYMBOLS:
                    continue
                try:
                    if exchange_id == "binance":
                        binance_symbol = _BINANCE_SYMBOL_MAP.get(symbol, f"{symbol}USDT")
                        resp = await self._http.get(
                            "https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": binance_symbol},
                        )
                        if resp.status_code == 200:
                            price = float(resp.json().get("price", 0))
                            if price > 0:
                                await self.on_reference_quote(
                                    Quote(symbol=symbol, last=price, timestamp=datetime.now(UTC))
                                )
                    elif exchange_id == "kucoin":
                        kucoin_symbol = _KUCOIN_SYMBOL_MAP.get(symbol, f"{symbol}-USDT")
                        resp = await self._http.get(
                            "https://api.kucoin.com/api/v1/market/orderbook/level1",
                            params={"symbol": kucoin_symbol},
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", {})
                            price = float(data.get("price", 0))
                            if price > 0:
                                await self.on_reference_quote(
                                    Quote(symbol=symbol, last=price, timestamp=datetime.now(UTC))
                                )
                except Exception as exc:
                    logger.warning("reference price fetch failed for %s:%s: %s", exchange_id, symbol, exc)

    async def _generate_tick(self, symbol: str) -> None:
        history = self._spot_history.get(symbol)
        if history and len(history) >= 2:
            spot = history[-1]
            reference = sum(history) / len(history)
            returns = [
                (history[i] - history[i - 1]) / history[i - 1] for i in range(1, len(history))
            ]
            volatility = _std(returns)
            momentum = _mean(returns[-5:]) if len(returns) >= 5 else _mean(returns)
        else:
            spot = 100.0
            reference = 100.0
            volatility = 0.0
            momentum = 0.0

        if not history or len(history) < 2:
            tick = Tick(
                timestamp=int(datetime.now(UTC).timestamp() * 1000),
                spot=spot,
                reference=reference,
                up_ask=0.5,
                down_ask=0.5,
                volatility=volatility,
                momentum=momentum,
            )
            self._store_tick(symbol, tick)
            return

        distance = (spot - reference) / max(reference, 1e-9)
        score = 140.0 * distance + 8.0 * momentum
        dampener = 1.0 + 10.0 * max(volatility, 0.0)
        p_up = 1.0 / (1.0 + math.exp(-score / dampener))
        noise = self._rng.gauss(0, 0.02)
        up_ask = max(0.01, min(0.99, p_up + noise))
        down_ask = max(0.01, min(0.99, 1.0 - up_ask + abs(noise) * 0.5))

        tick = Tick(
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            spot=spot,
            reference=reference,
            up_ask=up_ask,
            down_ask=down_ask,
            volatility=volatility,
            momentum=momentum,
        )
        self._store_tick(symbol, tick)

    def _store_tick(self, symbol: str, tick: Tick) -> None:
        self._ticks.setdefault(symbol, deque(maxlen=1000)).append(tick)
        self._last_tick_at = datetime.now(UTC)
        if self._reference_callback is not None:
            self._reference_callback(symbol, tick.spot)

    def stale_seconds(self) -> float | None:
        if self._last_tick_at is None:
            return None
        return max(0.0, (datetime.now(UTC) - self._last_tick_at).total_seconds())


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1))
