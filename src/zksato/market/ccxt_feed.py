from __future__ import annotations

import asyncio
import json
import logging
import random
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import httpx

from zksato.automation import AutomationEngine
from zksato.config import Settings
from zksato.domain import Quote
from zksato.observability import MARKET_FEED_AGE

logger = logging.getLogger(__name__)

_BINANCE_SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT",
    "BTC/USDT": "BTCUSDT",
    "BTC/THB": "BTCTHB",
    "ETH": "ETHUSDT",
    "ETH/USDT": "ETHUSDT",
    "ETH/THB": "ETHTHB",
    "SOL": "SOLUSDT",
    "SOL/USDT": "SOLUSDT",
    "SOL/THB": "SOLTHB",
    "BNB": "BNBUSDT",
    "BNB/USDT": "BNBUSDT",
    "BNB/THB": "BNBTHB",
    "USDT/THB": "USDTTHB",
    "USDC/THB": "USDCTHB",
    "XRP": "XRPUSDT",
    "XRP/THB": "XRPTHB",
    "DOGE": "DOGEUSDT",
    "DOGE/THB": "DOGETHB",
    "ADA": "ADAUSDT",
    "ADA/THB": "ADATHB",
    "AVAX": "AVAXUSDT",
    "AVAX/THB": "AVAXTHB",
    "DOT": "DOTUSDT",
    "DOT/THB": "DOTTHB",
    "MATIC": "MATICUSDT",
    "LINK": "LINKUSDT",
    "LINK/THB": "LINKTHB",
    "NEAR": "NEARUSDT",
    "NEAR/THB": "NEARTHB",
    "SUI": "SUIUSDT",
    "SUI/THB": "SUITHB",
    "PEPE": "PEPEUSDT",
    "PEPE/THB": "PEPETHB",
}

_KUCOIN_SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "BNB": "BNB-USDT",
    "XRP": "XRP-USDT",
    "DOGE": "DOGE-USDT",
    "ADA": "ADA-USDT",
    "AVAX": "AVAX-USDT",
    "DOT": "DOT-USDT",
    "MATIC": "MATIC-USDT",
    "LINK": "LINK-USDT",
}


class CcxtMarketFeed:
    """Public CCXT WebSocket/REST feed for Binance and KuCoin.

    This feed is isolated to paper and sandbox modes. It never receives
    or uses exchange API credentials for market data; public endpoints only.
    """

    def __init__(self, automation: AutomationEngine, settings: Settings) -> None:
        if not settings.ccxt_configured:
            raise RuntimeError("CCXT market feed is not configured")
        if settings.trading_mode not in {"paper", "sandbox"}:
            raise RuntimeError("CCXT public feed is restricted to paper/sandbox mode")
        self.automation = automation
        self.settings = settings
        self.running = False
        self._stop = asyncio.Event()
        self._main_task: asyncio.Task[None] | None = None
        self._http: httpx.AsyncClient | None = None
        self._last_message_at: datetime | None = None
        self._reconnect_count = 0
        self._last_error: str | None = None
        self._connected = False
        self._symbols: list[str] = []

    @property
    def _binance_rest_base(self) -> str:
        if self.settings.ccxt_sandbox:
            return "https://testnet.binance.vision/api"
        return "https://api.binance.com/api"

    @property
    def _binance_ws_base(self) -> str:
        if self.settings.ccxt_sandbox:
            return "wss://stream.testnet.binance.vision/stream"
        return "wss://stream.binance.com:9443/stream"

    def start(self, symbols: list[str]) -> None:
        if self.running:
            return
        self._symbols = sorted({s.strip().upper() for s in symbols if s.strip()})
        self.running = True
        self._stop = asyncio.Event()
        self._main_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.running = False
        self._stop.set()
        if self._main_task is not None:
            self._main_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._main_task
            self._main_task = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._connected = False

    def status(self) -> dict[str, object]:
        age: float | None = None
        if self._last_message_at is not None:
            age = max(0.0, (datetime.now(UTC) - self._last_message_at).total_seconds())
        return {
            "running": self.running,
            "connected": self._connected,
            "symbols": self._symbols,
            "last_message_at": self._last_message_at.isoformat() if self._last_message_at else None,
            "last_message_age_seconds": age,
            "stale": age is None or age > self.settings.market_data_stale_seconds,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
        }

    async def _run(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            ws_tasks: list[asyncio.Task[None]] = []
            try:
                self._http = httpx.AsyncClient(timeout=10.0)
                for exchange_id in self.settings.ccxt_exchange_list:
                    for symbol in self._symbols:
                        await self._fetch_snapshot(exchange_id, symbol)

                for exchange_id in self.settings.ccxt_exchange_list:
                    if exchange_id == "binance":
                        for symbol in self._symbols:
                            task = asyncio.create_task(self._binance_ws(symbol))
                            ws_tasks.append(task)
                    elif exchange_id == "kucoin":
                        task = asyncio.create_task(self._kucoin_ws())
                        ws_tasks.append(task)

                self._connected = True
                self._last_error = None
                delay = 1.0

                while not self._stop.is_set():
                    await asyncio.sleep(min(self.settings.poll_interval_seconds, 2.0))
                    if self._last_message_at is None:
                        continue
                    age = (datetime.now(UTC) - self._last_message_at).total_seconds()
                    if age > max(self.settings.market_data_stale_seconds * 3, 30.0):
                        raise RuntimeError("CCXT public feed stalled; reconnecting")

            except asyncio.CancelledError:
                raise
            except (RuntimeError, OSError, ConnectionError) as exc:
                self._last_error = str(exc)
                self._connected = False
                for task in ws_tasks:
                    task.cancel()
                await asyncio.gather(*ws_tasks, return_exceptions=True)
                self._reconnect_count += 1
                # Exponential backoff with uniform jitter (±20%)
                jitter = delay * (0.8 + 0.4 * (random.random() if "random" in globals() else 0.5))
                await asyncio.sleep(jitter)
                delay = min(delay * 2, 30.0)
            finally:
                if self._http is not None:
                    await self._http.aclose()
                    self._http = None
        self._connected = False

    async def _fetch_snapshot(self, exchange_id: str, symbol: str) -> None:
        if self._http is None:
            return
        try:
            if exchange_id == "binance":
                binance_symbol = _BINANCE_SYMBOL_MAP.get(symbol, f"{symbol}USDT")
                resp = await self._http.get(
                    f"{self._binance_rest_base}/v3/depth",
                    params={"symbol": binance_symbol, "limit": 1000},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    bids = data.get("bids", [])
                    asks = data.get("asks", [])
                    bid = float(bids[0][0]) if bids else None
                    offer = float(asks[0][0]) if asks else None
                    last_quote = self.automation.store.get_quote(symbol)
                    if last_quote is not None:
                        updated = last_quote.model_copy(
                            update={"bid": bid, "offer": offer, "timestamp": datetime.now(UTC)}
                        )
                        await self.automation.on_quote(updated)
                        self._last_message_at = datetime.now(UTC)
                        MARKET_FEED_AGE.set(0.0)
            elif exchange_id == "kucoin":
                kucoin_symbol = _KUCOIN_SYMBOL_MAP.get(symbol, f"{symbol}-USDT")
                resp = await self._http.get(
                    "https://api.kucoin.com/api/v1/market/orderbook/level2_100",
                    params={"symbol": kucoin_symbol},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    bids = data.get("bids", [])
                    asks = data.get("asks", [])
                    bid = float(bids[0][0]) if bids else None
                    offer = float(asks[0][0]) if asks else None
                    last_quote = self.automation.store.get_quote(symbol)
                    if last_quote is not None:
                        updated = last_quote.model_copy(
                            update={"bid": bid, "offer": offer, "timestamp": datetime.now(UTC)}
                        )
                        await self.automation.on_quote(updated)
                        self._last_message_at = datetime.now(UTC)
                        MARKET_FEED_AGE.set(0.0)
        except Exception as exc:
            logger.warning("snapshot fetch failed for %s:%s: %s", exchange_id, symbol, exc)

    async def _binance_ws(self, symbol: str) -> None:
        binance_symbol = _BINANCE_SYMBOL_MAP.get(symbol, f"{symbol}USDT").lower()
        streams = [
            f"{binance_symbol}@depth20@100ms",
            f"{binance_symbol}@trade",
            f"{binance_symbol}@ticker",
        ]
        url = f"{self._binance_ws_base}?streams={'/'.join(streams)}"
        backoff = 1.0
        while not self._stop.is_set():
            try:
                from websockets.asyncio.client import connect as ws_connect

                async with ws_connect(url) as ws:
                    backoff = 1.0
                    self._connected = True
                    async for message in ws:
                        if self._stop.is_set():
                            break
                        self._last_message_at = datetime.now(UTC)
                        payload = json.loads(message)
                        self._on_binance_message(payload, symbol)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = f"binance ws error: {exc}"
                logger.warning("binance ws reconnect for %s: %s", symbol, exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _kucoin_ws(self) -> None:
        url = "wss://stream.kucoin.com"
        topics = []
        for symbol in self._symbols:
            kucoin_symbol = _KUCOIN_SYMBOL_MAP.get(symbol, f"{symbol}-USDT")
            topics.append(f"/market/ticker:{kucoin_symbol}")
            topics.append(f"/market/level2:{kucoin_symbol}")
            topics.append(f"/market/match:{kucoin_symbol}")

        subscribe_messages = [
            {
                "id": str(idx + 1),
                "type": "subscribe",
                "topic": topic,
                "privateChannel": False,
                "response": True,
            }
            for idx, topic in enumerate(topics)
        ]
        backoff = 1.0
        while not self._stop.is_set():
            try:
                from websockets.asyncio.client import connect as ws_connect

                async with ws_connect(url) as ws:
                    backoff = 1.0
                    self._connected = True
                    for msg in subscribe_messages:
                        await ws.send(json.dumps(msg))
                    async for message in ws:
                        if self._stop.is_set():
                            break
                        self._last_message_at = datetime.now(UTC)
                        payload = json.loads(message)
                        self._on_kucoin_message(payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = f"kucoin ws error: {exc}"
                logger.warning("kucoin ws reconnect: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _on_binance_message(self, payload: dict[str, Any], symbol: str) -> None:
        stream = payload.get("stream", "")
        data = payload.get("data", payload)
        quote = None
        if "@depth20@100ms" in stream:
            bids = data.get("b", [])
            asks = data.get("a", [])
            bid = float(bids[0][0]) if bids else None
            offer = float(asks[0][0]) if asks else None
            last_quote = self.automation.store.get_quote(symbol)
            if last_quote is not None:
                quote = last_quote.model_copy(
                    update={"bid": bid, "offer": offer, "timestamp": datetime.now(UTC)}
                )
        elif "@trade" in stream:
            last = float(data.get("p", 0))
            quantity = float(data.get("q", 0))
            if last > 0:
                quote = Quote(
                    symbol=symbol,
                    last=last,
                    volume=quantity,
                    timestamp=datetime.now(UTC),
                )
        elif "@ticker" in stream:
            last = float(data.get("c", 0))
            if last > 0:
                quote = Quote(
                    symbol=symbol,
                    last=last,
                    bid=float(data["b"]) if data.get("b") else None,
                    offer=float(data["a"]) if data.get("a") else None,
                    volume=float(data.get("v", 0)),
                    timestamp=datetime.now(UTC),
                )
        if quote is not None:
            asyncio.get_running_loop().create_task(self.automation.on_quote(quote))
            MARKET_FEED_AGE.set(0.0)

    def _on_kucoin_message(self, payload: dict[str, Any]) -> None:
        topic = payload.get("topic", payload.get("subject", ""))
        data = payload.get("data", payload)
        symbol = None
        topic_symbol = topic.split(":")[-1] if ":" in topic else ""
        topic_symbol = topic_symbol.strip().upper()
        if topic_symbol in self._symbols:
            symbol = topic_symbol
        else:
            base = topic_symbol.split("-")[0] if "-" in topic_symbol else topic_symbol
            if base in self._symbols:
                symbol = base
        if symbol is None:
            return
        quote = None
        if topic.startswith("/market/ticker"):
            last = float(data.get("price", 0))
            if last > 0:
                quote = Quote(
                    symbol=symbol,
                    last=last,
                    bid=float(data["bestBid"]) if data.get("bestBid") else None,
                    offer=float(data["bestAsk"]) if data.get("bestAsk") else None,
                    volume=float(data.get("size", 0)),
                    timestamp=datetime.now(UTC),
                )
        elif topic.startswith("/market/level2"):
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            bid = float(bids[0][0]) if bids else None
            offer = float(asks[0][0]) if asks else None
            last_quote = self.automation.store.get_quote(symbol)
            if last_quote is not None:
                quote = last_quote.model_copy(
                    update={"bid": bid, "offer": offer, "timestamp": datetime.now(UTC)}
                )
        elif topic.startswith("/market/match"):
            last = float(data.get("price", 0))
            if last > 0:
                quote = Quote(
                    symbol=symbol,
                    last=last,
                    volume=float(data.get("size", 0)),
                    timestamp=datetime.now(UTC),
                )
        if quote is not None:
            asyncio.get_running_loop().create_task(self.automation.on_quote(quote))
            MARKET_FEED_AGE.set(0.0)
