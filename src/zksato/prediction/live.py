from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from zksato.config import Settings
from zksato.domain import Side


class PredictionVenueAdapter(ABC):
    """Abstract interface for external prediction market CLOB venues (e.g. Polymarket, Kalshi)."""

    @abstractmethod
    async def get_market_quote(self, market_id: str) -> dict[str, float]:
        """Fetch current best bid/ask and implied probability for binary outcomes."""
        pass

    @abstractmethod
    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        """Submit a guarded limit/market order to the venue."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open resting order on the venue."""
        pass


class PolymarketClobAdapter(PredictionVenueAdapter):
    """Audited read/write venue adapter scaffold for Polymarket CTF / CLOB."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    async def get_market_quote(self, market_id: str) -> dict[str, float]:
        # Return structured quote layout
        return {
            "market_id": market_id,
            "up_ask": 0.50,
            "up_bid": 0.49,
            "down_ask": 0.50,
            "down_bid": 0.49,
            "spread": 0.01,
        }

    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Polymarket venue credentials not configured")
        return {
            "order_id": f"poly-{market_id}-{side.value}",
            "status": "submitted",
            "side": side.value,
            "price": price,
            "order_usd": order_usd,
        }

    async def cancel_order(self, order_id: str) -> bool:
        return True


class PredictionLiveGate:
    """Guarded live-mode scaffold for prediction markets."""

    def __init__(self, settings: Settings, adapter: PredictionVenueAdapter | None = None) -> None:
        self.settings = settings
        self.adapter = adapter
        self.enable_live = settings.prediction_enable_live
        self.acknowledge_loss = False
        self.reviewed_adapter = False
        self.kill_switch_ready = False

    def validate(self) -> None:
        if not self.settings.prediction_enabled:
            raise RuntimeError("prediction market is not enabled")
        if not self.enable_live:
            raise RuntimeError("prediction live trading is disabled by server policy")
        if not self.acknowledge_loss:
            raise RuntimeError("live trading locked: acknowledge loss is required")
        if not self.reviewed_adapter:
            raise RuntimeError("live trading locked: adapter review is required")
        if not self.kill_switch_ready:
            raise RuntimeError("live trading locked: kill switch readiness is required")
        if self.adapter is None:
            raise RuntimeError("live trading locked: no reviewed venue adapter attached")
