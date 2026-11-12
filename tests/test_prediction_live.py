"""Tests for prediction live module."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zksato.broker.base import BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import Side
from zksato.prediction.live import (
    PolymarketClobAdapter,
    PredictionLiveGate,
    PredictionVenueAdapter,
)


class MockHttpClient:
    """Mock HTTP client for testing."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def _get_response(self, key: str) -> Any:
        resp = self.responses.get(key)
        if resp is None:
            # Return a default mock response with 404
            resp = MagicMock()
            resp.status_code = 404
            resp.json = lambda: {}
        return resp

    async def get(self, url: str, params: dict | None = None) -> Any:
        self.calls.append({"method": "GET", "url": url, "params": params})
        key = url
        if params:
            key += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return self._get_response(key)

    async def post(self, url: str, json: dict | None = None) -> Any:
        self.calls.append({"method": "POST", "url": url, "json": json})
        return self._get_response(url)

    async def delete(self, url: str) -> Any:
        self.calls.append({"method": "DELETE", "url": url})
        return self._get_response(url)

    async def aclose(self) -> None:
        pass


class TestPredictionVenueAdapter:
    def test_abstract_methods_exist(self) -> None:
        assert hasattr(PredictionVenueAdapter, "get_market_quote")
        assert hasattr(PredictionVenueAdapter, "place_order")
        assert hasattr(PredictionVenueAdapter, "cancel_order")


class TestPolymarketClobAdapter:
    @pytest.fixture
    def settings(self) -> Settings:
        return Settings(
            prediction_enabled=True,
            prediction_clob_api_key="test_key",
            prediction_clob_api_secret="test_secret",
            prediction_clob_passphrase="test_passphrase",
            prediction_clob_url="https://test.polymarket.com",
            prediction_clob_timeout_seconds=5.0,
            prediction_max_order_usd=10.0,
        )

    @pytest.fixture
    def mock_client(self) -> MockHttpClient:
        return MockHttpClient(
            {
                "https://test.polymarket.com/book?token_id=market_123": MagicMock(
                    status_code=200,
                    json=lambda: {
                        "up_ask": 0.55,
                        "down_ask": 0.45,
                        "up_bid": 0.54,
                        "down_bid": 0.44,
                    },
                ),
                "https://test.polymarket.com/order": MagicMock(
                    status_code=200,
                    json=lambda: {
                        "order_id": "order_123",
                        "market_id": "market_123",
                        "price": "0.55",
                        "size": "18.18",
                        "status": "open",
                    },
                ),
                "https://test.polymarket.com/order/order_123": MagicMock(
                    status_code=200, json=lambda: {"success": True}
                ),
            }
        )

    def test_init_with_settings(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        assert adapter.api_key == "test_key"
        assert adapter.api_secret == "test_secret"
        assert adapter.passphrase == "test_passphrase"
        assert adapter.base_url == "https://test.polymarket.com"
        assert adapter.timeout == 5.0

    def test_init_with_explicit_args(self) -> None:
        adapter = PolymarketClobAdapter(
            api_key="explicit_key",
            api_secret="explicit_secret",
            base_url="https://explicit.com",
            timeout=15.0,
        )
        assert adapter.api_key == "explicit_key"
        assert adapter.api_secret == "explicit_secret"
        assert adapter.base_url == "https://explicit.com"
        assert adapter.timeout == 15.0

    def test_validate_market_raises_on_empty(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        with pytest.raises(ValueError, match="market_id is required"):
            adapter._validate_market("")

    def test_validate_order_raises_on_invalid_price(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        with pytest.raises(ValueError, match="prediction price must be between 0 and 1"):
            adapter._validate_order(1.5, 10.0)
        with pytest.raises(ValueError, match="prediction price must be between 0 and 1"):
            adapter._validate_order(-0.1, 10.0)

    def test_validate_order_raises_on_invalid_order_usd(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        with pytest.raises(ValueError, match="order_usd must be positive"):
            adapter._validate_order(0.5, 0)
        with pytest.raises(ValueError, match="order_usd must be positive"):
            adapter._validate_order(0.5, -10.0)

    def test_validate_order_respects_max_order_usd(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        with pytest.raises(
            ValueError, match="prediction order exceeds configured per-order USD limit"
        ):
            adapter._validate_order(0.5, 15.0)

    def test_auth_headers_without_credentials(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=None, api_key=None, api_secret=None)
        headers = adapter._auth_headers()
        assert headers == {"Content-Type": "application/json"}

    def test_auth_headers_with_credentials(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=settings)
        headers = adapter._auth_headers("GET", "/test")
        assert "X-API-KEY" in headers
        assert "X-TIMESTAMP" in headers
        assert "X-SIGNATURE" in headers
        assert "X-PASSPHRASE" in headers

    @pytest.mark.asyncio
    async def test_get_market_quote_from_book_endpoint(
        self, settings: Settings, mock_client: MockHttpClient
    ) -> None:
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        quote = await adapter.get_market_quote("market_123")
        assert quote["market_id"] == "market_123"
        assert quote["up_ask"] == 0.55
        assert quote["down_ask"] == 0.45
        assert quote["up_bid"] == 0.54
        assert quote["down_bid"] == 0.44

    @pytest.mark.asyncio
    async def test_get_market_quote_from_bids_asks(self, settings: Settings) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/book?token_id=market_123": MagicMock(
                    status_code=200,
                    json=lambda: {"asks": [{"price": "0.51"}], "bids": [{"price": "0.49"}]},
                ),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        quote = await adapter.get_market_quote("market_123")
        assert quote["up_ask"] == 0.51
        # down_ask = 1.0 - bid_price = 1.0 - 0.49 = 0.51
        assert quote["down_ask"] == pytest.approx(0.51)
        assert quote["up_bid"] == 0.49
        # down_bid = 1.0 - ask_price = 1.0 - 0.51 = 0.49
        assert quote["down_bid"] == pytest.approx(0.49)

    @pytest.mark.asyncio
    async def test_get_market_quote_falls_back_to_price_endpoints(self, settings: Settings) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/book?token_id=market_123": MagicMock(status_code=404),
                "https://test.polymarket.com/price?side=buy&token_id=market_123": MagicMock(
                    status_code=200, json=lambda: {"price": "0.52"}
                ),
                "https://test.polymarket.com/price?side=sell&token_id=market_123": MagicMock(
                    status_code=200, json=lambda: {"price": "0.48"}
                ),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        quote = await adapter.get_market_quote("market_123")
        assert quote["up_ask"] == 0.52
        assert quote["down_ask"] == 0.48

    @pytest.mark.asyncio
    async def test_get_market_quote_falls_back_to_markets_endpoint(
        self, settings: Settings
    ) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/book?token_id=market_123": MagicMock(status_code=404),
                "https://test.polymarket.com/price?side=buy&token_id=market_123": MagicMock(
                    status_code=404
                ),
                "https://test.polymarket.com/price?side=sell&token_id=market_123": MagicMock(
                    status_code=404
                ),
                "https://test.polymarket.com/markets/market_123": MagicMock(
                    status_code=200,
                    json=lambda: {
                        "market_id": "market_123",
                        "price": "0.55",
                        "up_bid": "0.53",
                        "down_ask": "0.47",
                    },
                ),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        quote = await adapter.get_market_quote("market_123")
        assert quote["up_ask"] == 0.55
        assert quote["down_ask"] == 0.47

    @pytest.mark.asyncio
    async def test_get_market_quote_raises_on_not_found(self, settings: Settings) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/book?token_id=market_123": MagicMock(status_code=404),
                "https://test.polymarket.com/price?side=buy&token_id=market_123": MagicMock(
                    status_code=404
                ),
                "https://test.polymarket.com/price?side=sell&token_id=market_123": MagicMock(
                    status_code=404
                ),
                "https://test.polymarket.com/markets/market_123": MagicMock(status_code=404),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        with pytest.raises(RuntimeError, match="market not found"):
            await adapter.get_market_quote("market_123")

    @pytest.mark.asyncio
    async def test_place_order_success(
        self, settings: Settings, mock_client: MockHttpClient
    ) -> None:
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        result = await adapter.place_order("market_123", Side.UP, 0.55, 10.0)
        assert result["order_id"] == "order_123"
        assert result["side"] == "up"
        assert result["price"] == 0.55
        assert result["status"] == "open"

    @pytest.mark.asyncio
    async def test_place_order_requires_credentials(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=None, api_key=None, api_secret=None)
        with pytest.raises(
            RuntimeError, match="Polymarket mutation requires api_key and api_secret"
        ):
            await adapter.place_order("market_123", Side.UP, 0.55, 10.0)

    @pytest.mark.asyncio
    async def test_place_order_validates_side(
        self, settings: Settings, mock_client: MockHttpClient
    ) -> None:
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        with pytest.raises(ValueError, match="prediction adapter requires UP or DOWN side"):
            await adapter.place_order("market_123", Side.BUY, 0.55, 10.0)

    @pytest.mark.asyncio
    async def test_place_order_network_error_raises_ambiguous(self, settings: Settings) -> None:
        async def failing_post(*args, **kwargs):
            raise ConnectionError("Network down")

        mock_client = MockHttpClient({})
        mock_client.post = failing_post
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        with pytest.raises(BrokerAmbiguousError, match="Polymarket order response ambiguous"):
            await adapter.place_order("market_123", Side.UP, 0.55, 10.0)

    @pytest.mark.asyncio
    async def test_place_order_rejected_raises_runtime_error(self, settings: Settings) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/order": MagicMock(
                    status_code=400,
                    json=lambda: {"error": "Invalid price"},
                    text="Invalid price",
                ),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        with pytest.raises(RuntimeError, match="order rejected"):
            await adapter.place_order("market_123", Side.UP, 0.55, 10.0)

    @pytest.mark.asyncio
    async def test_cancel_order_success(
        self, settings: Settings, mock_client: MockHttpClient
    ) -> None:
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        result = await adapter.cancel_order("order_123")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, settings: Settings) -> None:
        mock_client = MockHttpClient(
            {
                "https://test.polymarket.com/order/order_123": MagicMock(status_code=404),
            }
        )
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        result = await adapter.cancel_order("order_123")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_order_requires_credentials(self, settings: Settings) -> None:
        adapter = PolymarketClobAdapter(settings=None, api_key=None, api_secret=None)
        with pytest.raises(RuntimeError, match="Polymarket cancel requires api_key and api_secret"):
            await adapter.cancel_order("order_123")

    @pytest.mark.asyncio
    async def test_cancel_order_network_error_raises_ambiguous(self, settings: Settings) -> None:
        async def failing_delete(*args, **kwargs):
            raise ConnectionError("Network down")

        mock_client = MockHttpClient({})
        mock_client.delete = failing_delete
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        with pytest.raises(BrokerAmbiguousError, match="Polymarket cancel response ambiguous"):
            await adapter.cancel_order("order_123")

    @pytest.mark.asyncio
    async def test_client_lifecycle_with_injected_client(
        self, settings: Settings, mock_client: MockHttpClient
    ) -> None:
        adapter = PolymarketClobAdapter(settings=settings, http_client=mock_client)
        await adapter.get_market_quote("market_123")
        # Injected client should not be closed
        assert len(mock_client.calls) == 1

    @pytest.mark.asyncio
    async def test_client_lifecycle_creates_own_client(self, settings: Settings) -> None:
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=MagicMock(
                    status_code=200, json=lambda: {"up_ask": 0.5, "down_ask": 0.5}
                )
            )
            mock_instance.aclose = AsyncMock()
            mock_client_class.return_value = mock_instance

            adapter = PolymarketClobAdapter(settings=settings)
            await adapter.get_market_quote("market_123")

            mock_client_class.assert_called_once()
            mock_instance.aclose.assert_called_once()


class TestPredictionLiveGate:
    @pytest.fixture
    def settings(self) -> Settings:
        return Settings(
            prediction_enabled=True,
            prediction_enable_live=False,
        )

    def test_validate_requires_prediction_enabled(self, settings: Settings) -> None:
        settings.prediction_enabled = False
        gate = PredictionLiveGate(settings=settings)
        with pytest.raises(RuntimeError, match="prediction market is not enabled"):
            gate.validate()

    def test_validate_requires_live_enabled(self, settings: Settings) -> None:
        settings.prediction_enable_live = False
        gate = PredictionLiveGate(settings=settings)
        with pytest.raises(RuntimeError, match="prediction live trading is disabled"):
            gate.validate()

    def test_validate_requires_acknowledge_loss(self, settings: Settings) -> None:
        settings.prediction_enable_live = True
        gate = PredictionLiveGate(settings=settings)
        gate.acknowledge_loss = False
        with pytest.raises(RuntimeError, match="acknowledge loss is required"):
            gate.validate()

    def test_validate_requires_reviewed_adapter(self, settings: Settings) -> None:
        settings.prediction_enable_live = True
        gate = PredictionLiveGate(settings=settings)
        gate.acknowledge_loss = True
        gate.reviewed_adapter = False
        with pytest.raises(RuntimeError, match="adapter review is required"):
            gate.validate()

    def test_validate_requires_kill_switch_ready(self, settings: Settings) -> None:
        settings.prediction_enable_live = True
        gate = PredictionLiveGate(settings=settings)
        gate.acknowledge_loss = True
        gate.reviewed_adapter = True
        gate.kill_switch_ready = False
        with pytest.raises(RuntimeError, match="kill switch readiness is required"):
            gate.validate()

    def test_validate_requires_adapter(self, settings: Settings) -> None:
        settings.prediction_enable_live = True
        gate = PredictionLiveGate(settings=settings)
        gate.acknowledge_loss = True
        gate.reviewed_adapter = True
        gate.kill_switch_ready = True
        gate.adapter = None
        with pytest.raises(RuntimeError, match="no reviewed venue adapter attached"):
            gate.validate()

    def test_validate_passes_when_all_conditions_met(self, settings: Settings) -> None:
        settings.prediction_enable_live = True
        gate = PredictionLiveGate(settings=settings)
        gate.acknowledge_loss = True
        gate.reviewed_adapter = True
        gate.kill_switch_ready = True
        gate.adapter = MagicMock(spec=PredictionVenueAdapter)
        gate.validate()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
