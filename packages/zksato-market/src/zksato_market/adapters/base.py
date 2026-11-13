"""Market data adapter protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from zksato_core.models import Bar, Quote

from zksato_market.types import Instrument, MarketType


class MarketDataAdapter(ABC):
    """Protocol for market data adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name."""
        ...

    @property
    @abstractmethod
    def market_type(self) -> MarketType:
        """Market type."""
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote | None:
        """Get current quote for symbol."""
        ...

    @abstractmethod
    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple symbols."""
        ...

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[Bar]:
        """Get historical bars."""
        ...

    @abstractmethod
    async def get_latest_bar(self, symbol: str, timeframe: str) -> Bar | None:
        """Get latest bar."""
        ...

    @abstractmethod
    async def get_instruments(self, market_type: MarketType | None = None) -> list[Instrument]:
        """Get instrument reference data."""
        ...

    @abstractmethod
    async def get_instrument(self, symbol: str) -> Instrument | None:
        """Get instrument by symbol."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check adapter health."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close adapter."""
        ...


class RESTAdapter(MarketDataAdapter):
    """Base REST adapter."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._session = None

    async def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
