"""Settrade REST adapter."""

from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator

from zksato_market.adapters.base import MarketDataAdapter, RESTAdapter
from zksato_market.types import MarketType, Instrument
from zksato_core.models import Quote, Trade, Bar
from zksato_core.money import Money
from zksato_core.exceptions import MarketDataError


class SettradeAdapter(MarketDataAdapter):
    """Settrade REST API adapter."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        broker_id: str,
        app_code: str,
        is_derivatives: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._broker_id = broker_id
        self._app_code = app_code
        self._is_derivatives = is_derivatives
        self._timeout = timeout
        self._client = None
        self._base_url = "https://api.settrade.com/v2"  # Placeholder

    @property
    def name(self) -> str:
        return "settrade"

    @property
    def market_type(self) -> MarketType:
        return MarketType.TFEX if self._is_derivatives else MarketType.EQUITY

    async def _get_client(self):
        """Get or create Settrade SDK client."""
        if self._client is None:
            # Import and initialize settrade-v2 SDK
            try:
                import settrade_v2
                self._client = settrade_v2.Client(
                    app_id=self._app_id,
                    app_secret=self._app_secret,
                    broker_id=self._broker_id,
                    app_code=self._app_code,
                    is_sandbox=True,  # Default to sandbox
                )
            except ImportError:
                raise MarketDataError("settrade-v2 SDK not installed")
        return self._client

    async def get_quote(self, symbol: str) -> Quote | None:
        """Get current quote for symbol."""
        client = await self._get_client()
        # Use Settrade SDK to get quote
        # market_data = client.MarketData()
        # quote = market_data.get_quote(symbol)
        # Convert to our Quote model
        return None  # Placeholder

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote:
                results[symbol] = quote
        return results

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[Bar]:
        """Get historical bars."""
        client = await self._get_client()
        # Use Settrade SDK to get historical data
        return []  # Placeholder

    async def get_latest_bar(self, symbol: str, timeframe: str) -> Bar | None:
        """Get latest bar."""
        bars = await self.get_bars(symbol, timeframe, datetime.now())
        return bars[-1] if bars else None

    async def get_instruments(self, market_type: MarketType | None = None) -> list[Instrument]:
        """Get instrument reference data."""
        client = await self._get_client()
        # Use Settrade SDK to get instrument list
        return []  # Placeholder

    async def get_instrument(self, symbol: str) -> Instrument | None:
        """Get instrument by symbol."""
        instruments = await self.get_instruments()
        for inst in instruments:
            if inst.symbol == symbol:
                return inst
        return None

    async def health_check(self) -> bool:
        """Check adapter health."""
        try:
            client = await self._get_client()
            # Try a simple API call
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close adapter."""
        if self._client:
            # Close Settrade client if needed
            pass