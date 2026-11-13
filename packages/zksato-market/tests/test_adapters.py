"""Tests for zksato-market adapters."""

from zksato_market.adapters import CCXTAdapter, MarketDataAdapter, SettradeAdapter
from zksato_market.types import MarketType


def test_adapter_protocol():
    """Test that adapter classes implement the protocol."""
    assert hasattr(MarketDataAdapter, "name")
    assert hasattr(MarketDataAdapter, "market_type")
    assert hasattr(MarketDataAdapter, "get_quote")
    assert hasattr(MarketDataAdapter, "get_quotes")
    assert hasattr(MarketDataAdapter, "get_bars")
    assert hasattr(MarketDataAdapter, "get_latest_bar")
    assert hasattr(MarketDataAdapter, "get_instruments")
    assert hasattr(MarketDataAdapter, "get_instrument")
    assert hasattr(MarketDataAdapter, "health_check")
    assert hasattr(MarketDataAdapter, "close")


def test_settrade_adapter_creation():
    adapter = SettradeAdapter(
        app_id="test",
        app_secret="test",
        broker_id="test",
        app_code="test",
    )
    assert adapter.name == "settrade"
    assert adapter.market_type == MarketType.EQUITY


def test_settrade_adapter_derivatives():
    adapter = SettradeAdapter(
        app_id="test",
        app_secret="test",
        broker_id="test",
        app_code="test",
        is_derivatives=True,
    )
    assert adapter.market_type == MarketType.TFEX


def test_ccxt_adapter_creation():
    adapter = CCXTAdapter("binance", sandbox=True)
    assert adapter.name == "ccxt_binance"
    assert adapter.market_type == MarketType.CRYPTO


def test_ccxt_adapter_with_credentials():
    adapter = CCXTAdapter(
        "binance",
        api_key="test_key",
        secret="test_secret",
        sandbox=True,
    )
    assert adapter.api_key == "test_key"
    assert adapter.secret == "test_secret"
