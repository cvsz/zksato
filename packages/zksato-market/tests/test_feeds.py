"""Tests for zksato-market feeds."""

from datetime import datetime

from zksato_core.models import Quote
from zksato_core.money import thb
from zksato_market.feeds import (
    BinanceFeed,
    FeedMetrics,
    ReplayEvent,
    ReplayFeed,
    SettradeFeed,
)
from zksato_market.types import MarketType


def test_feed_metrics():
    metrics = FeedMetrics()
    assert metrics.messages_received == 0
    assert metrics.messages_processed == 0
    assert metrics.errors == 0


def test_settrade_feed_creation():
    feed = SettradeFeed(
        app_id="test",
        app_secret="test",
        broker_id="test",
        app_code="test",
    )
    assert feed.name == "settrade"
    assert feed.market_type == MarketType.EQUITY


def test_binance_feed_creation():
    feed = BinanceFeed(api_key="test", secret="test", sandbox=True)
    assert feed.name == "ccxt_binance"
    assert feed.market_type == MarketType.CRYPTO


def test_replay_feed():
    feed = ReplayFeed("test_replay", MarketType.EQUITY, speed=1.0)
    assert feed.name == "test_replay"
    assert feed.speed == 1.0

    # Add events
    quote = Quote(symbol="AOT", last=thb(50), timestamp=datetime.now())
    feed.add_quote(datetime.now(), quote)
    assert len(feed.events) == 1


def test_replay_event():
    quote = Quote(symbol="AOT", last=thb(50), timestamp=datetime.now())
    event = ReplayEvent(
        timestamp=datetime.now(),
        event_type="quote",
        data=quote,
    )
    assert event.event_type == "quote"
    assert event.data == quote
