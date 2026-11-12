"""Tests for prediction market feed."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from zksato.config import Settings
from zksato.domain import Quote
from zksato.market.prediction_feed import PredictionMarketFeed
from zksato.prediction.core import Tick


def _make_settings(**kwargs) -> Settings:
    defaults = {
        "prediction_enabled": True,
        "ccxt_enabled": True,
        "ccxt_exchanges": "binance",
        "ccxt_sandbox": True,
        "market_data_stale_seconds": 10.0,
        "poll_interval_seconds": 2.0,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


class MockHttpClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    async def get(self, url: str, params: dict | None = None) -> Any:
        self.calls.append({"method": "GET", "url": url, "params": params})
        key = url
        if params:
            key += "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        resp = self.responses.get(key)
        if resp is None:
            resp = MagicMock()
            resp.status_code = 404
            resp.json = lambda: {}
        return resp

    async def aclose(self) -> None:
        pass


class TestPredictionMarketFeed:
    @pytest.fixture
    def settings(self) -> Settings:
        return _make_settings()

    @pytest.mark.asyncio
    async def test_start_and_stop(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC", "ETH"])
        assert feed.running is True
        assert feed._symbols == ["BTC", "ETH"]
        await feed.stop()
        assert feed.running is False

    @pytest.mark.asyncio
    async def test_status_when_not_started(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        status = feed.status()
        assert status["running"] is False
        assert status["symbols"] == []
        assert status["last_tick_at"] is None
        assert status["stale"] is True

    @pytest.mark.asyncio
    async def test_status_when_running(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        status = feed.status()
        assert status["running"] is True
        assert status["symbols"] == ["BTC"]
        await feed.stop()

    @pytest.mark.asyncio
    async def test_on_reference_quote(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        
        quote = Quote(symbol="BTC", last=50000.0, timestamp=datetime.now(UTC))
        await feed.on_reference_quote(quote)
        
        history = feed._spot_history["BTC"]
        assert len(history) == 1
        assert history[0] == 50000.0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_on_reference_quote_ignores_unknown_symbol(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        
        quote = Quote(symbol="ETH", last=3000.0, timestamp=datetime.now(UTC))
        await feed.on_reference_quote(quote)
        
        assert "ETH" not in feed._spot_history
        await feed.stop()

    @pytest.mark.asyncio
    async def test_get_ticks(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        
        # Generate a tick manually
        tick = Tick(
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            spot=50000.0,
            reference=50000.0,
            up_ask=0.55,
            down_ask=0.45,
        )
        feed._store_tick("BTC", tick)
        
        ticks = feed.get_ticks("BTC", limit=10)
        assert len(ticks) == 1
        assert ticks[0].spot == 50000.0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_generate_tick_without_history(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        
        await feed._generate_tick("BTC")
        
        ticks = feed.get_ticks("BTC")
        assert len(ticks) == 1
        assert ticks[0].spot == 100.0
        assert ticks[0].reference == 100.0
        assert ticks[0].up_ask == 0.5
        assert ticks[0].down_ask == 0.5
        await feed.stop()

    @pytest.mark.asyncio
    async def test_generate_tick_with_history(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        
        # Add some history
        feed._spot_history["BTC"].extend([50000.0, 50100.0, 50200.0, 50300.0, 50400.0])
        
        await feed._generate_tick("BTC")
        
        ticks = feed.get_ticks("BTC")
        assert len(ticks) == 1
        assert ticks[0].spot == 50400.0
        assert ticks[0].reference == pytest.approx(50200.0)
        assert 0.01 <= ticks[0].up_ask <= 0.99
        assert 0.01 <= ticks[0].down_ask <= 0.99
        await feed.stop()

    @pytest.mark.asyncio
    async def test_stale_seconds(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        assert feed.stale_seconds() is None
        
        feed.start(["BTC"])
        tick = Tick(
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            spot=50000.0,
            reference=50000.0,
            up_ask=0.55,
            down_ask=0.45,
        )
        feed._store_tick("BTC", tick)
        
        stale = feed.stale_seconds()
        assert stale is not None
        assert stale >= 0.0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_refresh_reference_prices_binance(self, settings: Settings) -> None:
        mock_client = MockHttpClient({
            "https://testnet.binance.vision/api/v3/ticker/price?symbol=BTCUSDT": MagicMock(
                status_code=200, json=lambda: {"price": "50000.0"}
            ),
        })
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        feed._http = mock_client
        await feed._refresh_reference_prices()
        
        history = feed._spot_history["BTC"]
        assert len(history) == 1
        assert history[0] == 50000.0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_refresh_reference_prices_kucoin(self, settings: Settings) -> None:
        settings.ccxt_exchanges = "kucoin"
        mock_client = MockHttpClient({
            "https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT": MagicMock(
                status_code=200, json=lambda: {"data": {"price": "50000.0"}}
            ),
        })
        feed = PredictionMarketFeed(settings)
        feed.start(["BTC"])
        feed._http = mock_client
        await feed._refresh_reference_prices()
        
        history = feed._spot_history["BTC"]
        assert len(history) == 1
        assert history[0] == 50000.0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_refresh_reference_prices_ignores_non_crypto(self, settings: Settings) -> None:
        feed = PredictionMarketFeed(settings)
        feed.start(["AAPL"])  # Not in _CRYPTO_SYMBOLS
        
        mock_client = MockHttpClient({})
        feed._http = mock_client
        await feed._refresh_reference_prices()
        
        # Should not fetch for non-crypto symbols - history should remain empty
        history = feed._spot_history.get("AAPL")
        assert history is not None and len(history) == 0
        await feed.stop()

    @pytest.mark.asyncio
    async def test_reference_callback(self, settings: Settings) -> None:
        callback_results: list[tuple[str, float]] = []
        
        def callback(symbol: str, price: float) -> None:
            callback_results.append((symbol, price))
        
        feed = PredictionMarketFeed(settings, reference_callback=callback)
        feed.start(["BTC"])
        
        tick = Tick(
            timestamp=int(datetime.now(UTC).timestamp() * 1000),
            spot=50000.0,
            reference=50000.0,
            up_ask=0.55,
            down_ask=0.45,
        )
        feed._store_tick("BTC", tick)
        
        assert len(callback_results) == 1
        assert callback_results[0] == ("BTC", 50000.0)
        await feed.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])