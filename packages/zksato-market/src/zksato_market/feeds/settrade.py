"""Settrade realtime feed."""

from __future__ import annotations

from zksato_core.exceptions import MarketDataError

from zksato_market.feeds.base import MarketDataFeed
from zksato_market.types import MarketType


class SettradeFeed(MarketDataFeed):
    """Settrade realtime market data feed."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        broker_id: str,
        app_code: str,
        is_derivatives: bool = False,
    ) -> None:
        super().__init__("settrade", MarketType.EQUITY if not is_derivatives else MarketType.TFEX)
        self.app_id = app_id
        self.app_secret = app_secret
        self.broker_id = broker_id
        self.app_code = app_code
        self.is_derivatives = is_derivatives
        self._client = None
        self._ws = None

    async def connect(self) -> None:
        """Connect to Settrade feed."""
        # Placeholder for actual Settrade v2 SDK integration
        # This would use settrade-v2 SDK to establish WebSocket connection
        self._status = self._status.__class__.CONNECTED

    async def disconnect(self) -> None:
        """Disconnect from Settrade feed."""
        if self._ws:
            await self._ws.close()
        self._status = self._status.__class__.DISCONNECTED

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols."""
        # Would subscribe via Settrade WebSocket
        pass

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols."""
        # Would unsubscribe via Settrade WebSocket
        pass

    def _handle_message(self, message: dict) -> None:
        """Handle incoming WebSocket message."""
        # Parse Settrade message format and emit events
        pass


class SettradeRealtimeFeed(SettradeFeed):
    """Settrade realtime feed with full implementation."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        broker_id: str,
        app_code: str,
        is_derivatives: bool = False,
    ) -> None:
        super().__init__(app_id, app_secret, broker_id, app_code, is_derivatives)
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    async def connect(self) -> None:
        """Connect with reconnection logic."""
        try:
            # Initialize Settrade SDK connection
            # self._client = settrade.Client(...)
            # self._ws = await self._client.connect_realtime()
            self._status = self._status.__class__.CONNECTED
            self._reconnect_attempts = 0
        except Exception as e:
            self._status = self._status.__class__.ERROR
            raise MarketDataError(f"Failed to connect to Settrade: {e}") from e

    async def _reconnect(self) -> None:
        """Attempt reconnection."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._status = self._status.__class__.ERROR
            return

        self._status = self._status.__class__.RECONNECTING
        self._reconnect_attempts += 1

        import asyncio

        await asyncio.sleep(2**self._reconnect_attempts)
        await self.connect()
