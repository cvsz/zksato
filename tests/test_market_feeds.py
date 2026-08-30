from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from zksato.automation import AutomationEngine
from zksato.config import Settings
from zksato.domain import Quote
from zksato.market.ccxt_feed import CcxtMarketFeed
from zksato.market.demo import DemoMarketFeed
from zksato.market.prediction_feed import PredictionMarketFeed
from zksato.store import StateStore


@pytest.fixture
def mock_automation() -> AutomationEngine:
    settings = Settings(trading_mode="paper")
    store = StateStore()
    service = AsyncMock()
    return AutomationEngine(settings=settings, store=store, service=service)


@pytest.mark.asyncio
async def test_demo_market_feed_generates_quotes(mock_automation: AutomationEngine) -> None:
    feed = DemoMarketFeed(mock_automation)
    assert feed.running is False
    feed.start(["AOT", "PTT"])
    assert feed.running is True
    feed.start(["AOT"])  # no-op when running
    await asyncio.sleep(0.05)
    quote = mock_automation.store.get_quote("AOT")
    assert quote is not None
    assert quote.symbol == "AOT"
    assert quote.bid <= quote.last <= quote.offer
    await feed.stop()
    assert feed.running is False


def test_ccxt_market_feed_validates_mode_and_config(mock_automation: AutomationEngine) -> None:
    # Unconfigured
    unconf_settings = Settings(ccxt_enabled=False)
    with pytest.raises(RuntimeError, match="not configured"):
        CcxtMarketFeed(mock_automation, unconf_settings)

    # Live mode prohibited
    live_settings = Settings(
        ccxt_enabled=True,
        ccxt_exchanges="binance",
        trading_mode="live",
        live_trading_enabled=True,
    )
    with pytest.raises(RuntimeError, match="restricted to paper/sandbox"):
        CcxtMarketFeed(mock_automation, live_settings)


@pytest.mark.asyncio
async def test_ccxt_market_feed_start_stop_and_status(mock_automation: AutomationEngine) -> None:
    settings = Settings(
        ccxt_enabled=True,
        ccxt_exchanges="binance,kucoin",
        trading_mode="paper",
    )
    feed = CcxtMarketFeed(mock_automation, settings)
    status_before = feed.status()
    assert status_before["running"] is False
    assert status_before["connected"] is False

    with patch.object(feed, "_run", new_callable=AsyncMock):
        feed.start(["btc", "eth"])
        assert feed.running is True
        assert feed._symbols == ["BTC", "ETH"]

        feed.start(["btc"])  # no-op if already running

        status_running = feed.status()
        assert status_running["running"] is True
        assert status_running["symbols"] == ["BTC", "ETH"]

        await feed.stop()
        assert feed.running is False


@pytest.mark.asyncio
async def test_prediction_market_feed_lifecycle_and_ticks() -> None:
    settings = Settings(prediction_enabled=True)
    called = {}

    def ref_callback(symbol: str, price: float) -> None:
        called[symbol] = price

    feed = PredictionMarketFeed(settings, reference_callback=ref_callback)
    status_init = feed.status()
    assert status_init["running"] is False

    # Test reference quote ingestion
    q = Quote(symbol="BTC", last=50000.0, timestamp=datetime.now(UTC))
    await feed.on_reference_quote(q)
    assert "BTC" not in called  # not yet started with symbols

    feed.start(["btc", "eth"])
    assert feed.running is True
    assert feed._symbols == ["BTC", "ETH"]

    await feed.on_reference_quote(q)
    assert called.get("BTC") == 50000.0

    # Ingest multiple prices to build history
    await feed.on_reference_quote(Quote(symbol="BTC", last=50500.0, timestamp=datetime.now(UTC)))
    await feed.on_reference_quote(Quote(symbol="BTC", last=51000.0, timestamp=datetime.now(UTC)))

    # Test tick generation
    await feed._generate_tick("BTC")
    ticks = feed.get_ticks("BTC")
    assert len(ticks) >= 1
    latest_tick = ticks[-1]
    assert latest_tick.spot == 51000.0
    assert latest_tick.up_ask > 0
    assert latest_tick.down_ask > 0

    await feed.stop()
    assert feed.running is False
