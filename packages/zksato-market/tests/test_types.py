"""Tests for zksato-market types."""

import pytest
from datetime import datetime

from zksato_market.types import (
    MarketType,
    FeedStatus,
    Quote,
    Trade,
    Bar,
    Instrument,
    FeedEvent,
    FeedConfig,
)
from zksato_core.money import thb, Money


def test_market_type():
    assert MarketType.EQUITY == "equity"
    assert MarketType.TFEX == "tfex"
    assert MarketType.CRYPTO == "crypto"
    assert MarketType.PREDICTION == "prediction"


def test_feed_status():
    assert FeedStatus.CONNECTING == "connecting"
    assert FeedStatus.CONNECTED == "connected"
    assert FeedStatus.DISCONNECTED == "disconnected"
    assert FeedStatus.ERROR == "error"
    assert FeedStatus.RECONNECTING == "reconnecting"


def test_quote():
    quote = Quote(
        symbol="AOT",
        last=thb(50),
        bid=thb(49.50),
        offer=thb(50.50),
        high=thb(52),
        low=thb(48),
        open=thb(49),
        previous_close=thb(48.50),
        volume=10000,
        value=thb(500000),
        timestamp=datetime.now(),
        source="test",
    )
    assert quote.symbol == "AOT"
    assert quote.change_pct == pytest.approx(3.09, rel=0.01)
    assert quote.spread == thb(1.0)
    assert quote.spread_pct == pytest.approx(2.0, rel=0.01)


def test_trade():
    trade = Trade(
        symbol="AOT",
        price=thb(50),
        quantity=100,
        side="buy",
        timestamp=datetime.now(),
        trade_id="123",
        source="test",
    )
    assert trade.symbol == "AOT"
    assert trade.side == "buy"


def test_bar():
    bar = Bar(
        symbol="AOT",
        timeframe="1m",
        timestamp=datetime.now(),
        open=thb(49),
        high=thb(52),
        low=thb(48),
        close=thb(50),
        volume=10000,
        value=thb(500000),
        source="test",
    )
    assert bar.symbol == "AOT"
    assert bar.timeframe == "1m"


def test_instrument():
    inst = Instrument(
        symbol="AOT",
        name="Airports of Thailand",
        market_type=MarketType.EQUITY,
        tick_size=thb(0.01),
        board_lot=100,
        price_band_pct=10.0,
        sector="Transportation",
    )
    assert inst.symbol == "AOT"
    assert inst.board_lot == 100


def test_feed_event():
    event = FeedEvent(
        event_type="quote",
        data={"symbol": "AOT", "price": 50},
        timestamp=datetime.now(),
        source="test",
    )
    assert event.event_type == "quote"


def test_feed_config():
    config = FeedConfig(
        name="test_feed",
        market_type=MarketType.EQUITY,
        symbols=["AOT", "PTT"],
        enabled=True,
        priority=1,
        config={"key": "value"},
    )
    assert config.name == "test_feed"
    assert config.symbols == ["AOT", "PTT"]