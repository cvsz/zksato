"""CCXT REST adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from zksato_core.models import Bar, Quote
from zksato_core.money import Money

from zksato_market.adapters.base import MarketDataAdapter
from zksato_market.types import Instrument, MarketType


class CCXTAdapter(MarketDataAdapter):
    """CCXT REST API adapter for crypto exchanges."""

    def __init__(
        self,
        exchange_id: str,
        api_key: str | None = None,
        secret: str | None = None,
        password: str | None = None,
        sandbox: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.sandbox = sandbox
        self.timeout = timeout
        self._exchange = None

    @property
    def name(self) -> str:
        return f"ccxt_{self.exchange_id}"

    @property
    def market_type(self) -> MarketType:
        return MarketType.CRYPTO

    async def _get_exchange(self):
        """Get or create CCXT exchange instance."""
        if self._exchange is None:
            import ccxt

            exchange_class = getattr(ccxt, self.exchange_id)
            config = {
                "apiKey": self.api_key,
                "secret": self.secret,
                "timeout": int(self.timeout * 1000),
                "enableRateLimit": True,
            }
            if self.password:
                config["password"] = self.password

            if self.sandbox:
                config["options"] = {"defaultType": "spot"}

            self._exchange = exchange_class(config)

            if self.sandbox and hasattr(self._exchange, "set_sandbox_mode"):
                self._exchange.set_sandbox_mode(True)

            await self._exchange.load_markets()

        return self._exchange

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get current quote for symbol."""
        exchange = await self._get_exchange()
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return self._convert_ticker(symbol, ticker)
        except Exception:
            return None

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple symbols."""
        exchange = await self._get_exchange()
        results = {}
        try:
            tickers = await exchange.fetch_tickers(symbols)
            for symbol, ticker in tickers.items():
                quote = self._convert_ticker(symbol, ticker)
                if quote:
                    results[symbol] = quote
        except Exception:
            for symbol in symbols:
                quote = await self.get_quote(symbol)
                if quote:
                    results[symbol] = quote
        return results

    def _convert_ticker(self, symbol: str, ticker: dict[str, Any]) -> Quote:
        """Convert CCXT ticker to Quote."""
        return Quote(
            symbol=symbol,
            last=Money(str(ticker.get("last", 0))),
            bid=Money(str(ticker.get("bid", 0))) if ticker.get("bid") else None,
            offer=Money(str(ticker.get("ask", 0))) if ticker.get("ask") else None,
            high=Money(str(ticker.get("high", 0))) if ticker.get("high") else None,
            low=Money(str(ticker.get("low", 0))) if ticker.get("low") else None,
            open=Money(str(ticker.get("open", 0))) if ticker.get("open") else None,
            previous_close=Money(str(ticker.get("previousClose", 0)))
            if ticker.get("previousClose")
            else None,
            volume=int(ticker.get("baseVolume", 0)),
            value=Money(str(ticker.get("quoteVolume", 0))),
            timestamp=datetime.fromtimestamp(ticker.get("timestamp", 0) / 1000)
            if ticker.get("timestamp")
            else datetime.now(),
            source=self.name,
        )

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[Bar]:
        """Get historical bars."""
        exchange = await self._get_exchange()
        try:
            since = int(start.timestamp() * 1000)
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            return self._convert_ohlcv(symbol, timeframe, ohlcv)
        except Exception:
            return []

    def _convert_ohlcv(self, symbol: str, timeframe: str, ohlcv: list[list]) -> list[Bar]:
        """Convert CCXT OHLCV to Bar list."""
        bars = [
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(candle[0] / 1000),
                open=Money(str(candle[1])),
                high=Money(str(candle[2])),
                low=Money(str(candle[3])),
                close=Money(str(candle[4])),
                volume=int(candle[5]),
                source=self.name,
            )
            for candle in ohlcv
        ]
        return bars

    async def get_latest_bar(self, symbol: str, timeframe: str) -> Bar | None:
        """Get latest bar."""
        bars = await self.get_bars(symbol, timeframe, datetime.now())
        return bars[-1] if bars else None

    async def get_instruments(self, market_type: MarketType | None = None) -> list[Instrument]:
        """Get instrument reference data."""
        exchange = await self._get_exchange()
        instruments = []

        for symbol, market in exchange.markets.items():
            if market_type and market.get("type") != market_type.value:
                continue

            instruments.append(
                Instrument(
                    symbol=symbol,
                    name=market.get("name", symbol),
                    market_type=MarketType.CRYPTO,
                    tick_size=Money(str(market.get("precision", {}).get("price", 0.01))),
                    board_lot=1,
                    sector="crypto",
                )
            )

        return instruments

    async def get_instrument(self, symbol: str) -> Instrument | None:
        """Get instrument by symbol."""
        exchange = await self._get_exchange()
        if symbol in exchange.markets:
            market = exchange.markets[symbol]
            return Instrument(
                symbol=symbol,
                name=market.get("name", symbol),
                market_type=MarketType.CRYPTO,
                tick_size=Money(str(market.get("precision", {}).get("price", 0.01))),
                board_lot=1,
                sector="crypto",
            )
        return None

    async def health_check(self) -> bool:
        """Check adapter health."""
        try:
            exchange = await self._get_exchange()
            await exchange.fetch_status()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close adapter."""
        if self._exchange:
            await self._exchange.close()
            self._exchange = None
