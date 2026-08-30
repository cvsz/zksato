from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from zksato.config import Settings
from zksato.domain import Side


class PredictionVenueAdapter(ABC):
    """Abstract interface for external prediction market CLOB venues (e.g. Polymarket, Kalshi)."""

    @abstractmethod
    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
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
    """Audited read/write venue adapter scaffold for Polymarket CTF / CLOB.

    This adapter is intentionally unimplemented.  Real Polymarket CLOB / CTF
    API integration (authentication, order signing, REST calls) has not been
    wired yet.  All methods raise ``NotImplementedError`` so that any accidental
    call to a live or paper path that reaches this adapter fails loudly rather
    than silently returning fabricated data.

    To enable live prediction-market execution, supply a concrete implementation
    that satisfies the ``PredictionVenueAdapter`` contract and pass it to
    ``PredictionLiveGate``.
    """

    _NOT_WIRED = (
        "PolymarketClobAdapter: HTTP / CLOB integration is not yet wired. "
        "Provide a concrete PredictionVenueAdapter implementation."
    )

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
        """Not implemented — raises to prevent silent use of placeholder data."""
        raise NotImplementedError(self._NOT_WIRED)

    async def place_order(
        self, market_id: str, side: Side, price: float, order_usd: float
    ) -> dict[str, Any]:
        """Not implemented — raises to prevent accidental live-money calls."""
        raise NotImplementedError(self._NOT_WIRED)

    async def cancel_order(self, order_id: str) -> bool:
        """Not implemented — raises to prevent silent no-ops."""
        raise NotImplementedError(self._NOT_WIRED)


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
