"""CCXT WebSocket feeds."""

from __future__ import annotations

from zksato_market.feeds.base import MarketDataFeed
from zksato_market.types import MarketType
from zksato_core.models import Quote, Trade, Bar
from zksato_core.exceptions import MarketDataError
from zksato_core.money import Money


class CCXTFeed(MarketDataFeed):
    """CCXT WebSocket feed for crypto exchanges."""

    def __init__(
        self,
        exchange_id: str,
        api_key: str | None = None,
        secret: str | None = None,
        password: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__(f"ccxt_{exchange_id}", MarketType.CRYPTO)
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.sandbox = sandbox
        self._exchange = None
        self._ws = None

    async def connect(self) -> None:
        """Connect to exchange WebSocket."""
        # Placeholder for CCXT WebSocket connection
        # Would use ccxt.pro for WebSocket support
        self._status = self._status.__class__.CONNECTED

    async def disconnect(self) -> None:
        """Disconnect from exchange WebSocket."""
        if self._ws:
            await self._ws.close()
        self._status = self._status.__class__.DISCONNECTED

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols."""
        # Would subscribe via CCXT WebSocket
        pass

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols."""
        pass


class BinanceFeed(CCXTFeed):
    """Binance WebSocket feed."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__("binance", api_key, secret, sandbox=sandbox)


class BinanceTHFeed(CCXTFeed):
    """Binance TH WebSocket feed."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__("binanceth", api_key, secret, sandbox=sandbox)


class KuCoinFeed(CCXTFeed):
    """KuCoin WebSocket feed."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        password: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__("kucoin", api_key, secret, password, sandbox)


class OKXFeed(CCXTFeed):
    """OKX WebSocket feed."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        password: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__("okx", api_key, secret, password, sandbox)


class BybitFeed(CCXTFeed):
    """Bybit WebSocket feed."""

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ) -> None:
        super().__init__("bybit", api_key, secret, sandbox=sandbox)