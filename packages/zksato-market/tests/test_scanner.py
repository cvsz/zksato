"""Tests for zksato-market scanner."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from zksato_market.scanner import MarketScanner, MultiMarketScanner, ScanFilter
from zksato_market.adapters.base import MarketDataAdapter
from zksato_market.types import Quote
from zksato_core.models import ScannerResult
from zksato_core.money import thb
from datetime import datetime


class MockAdapter(MarketDataAdapter):
    """Mock adapter for testing."""

    def __init__(self, quotes: dict[str, Quote]):
        self._quotes = quotes
        self._name = "mock"
        self._market_type = "test"

    @property
    def name(self) -> str:
        return self._name

    @property
    def market_type(self):
        return self._market_type

    async def get_quote(self, symbol: str):
        return self._quotes.get(symbol)

    async def get_quotes(self, symbols: list[str]):
        return {s: self._quotes[s] for s in symbols if s in self._quotes}

    async def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime | None = None, limit: int = 1000):
        return []

    async def get_latest_bar(self, symbol: str, timeframe: str):
        return None

    async def get_instruments(self, market_type=None):
        return []

    async def get_instrument(self, symbol: str):
        return None

    async def health_check(self):
        return True

    async def close(self):
        pass


@pytest.fixture
def sample_quotes():
    return {
        "AOT": Quote(symbol="AOT", last=thb(50), bid=thb(49.5), offer=thb(50.5), volume=10000, timestamp=datetime.now()),
        "PTT": Quote(symbol="PTT", last=thb(40), bid=thb(39.5), offer=thb(40.5), volume=20000, timestamp=datetime.now()),
        "CPALL": Quote(symbol="CPALL", last=thb(60), bid=thb(59.5), offer=thb(60.5), volume=5000, timestamp=datetime.now()),
    }


@pytest.fixture
def mock_adapter(sample_quotes):
    return MockAdapter(sample_quotes)


@pytest.fixture
def scanner(mock_adapter):
    return MarketScanner(mock_adapter)


@pytest.mark.asyncio
async def test_scan_all_symbols(scanner):
    results = await scanner.scan(["AOT", "PTT", "CPALL"])
    assert len(results) == 3
    assert all(isinstance(r, ScannerResult) for r in results)


@pytest.mark.asyncio
async def test_scan_with_filter(scanner):
    filter_criteria = ScanFilter(min_price=50)
    results = await scanner.scan(["AOT", "PTT", "CPALL"], filter_criteria)
    assert len(results) == 2  # AOT and CPALL >= 50
    assert all(r.last.amount >= 50 for r in results)


@pytest.mark.asyncio
async def test_scan_with_exclude(scanner):
    filter_criteria = ScanFilter(exclude_symbols=["PTT"])
    results = await scanner.scan(["AOT", "PTT", "CPALL"], filter_criteria)
    assert len(results) == 2
    assert all(r.symbol != "PTT" for r in results)


@pytest.mark.asyncio
async def test_scan_sorting(scanner):
    results = await scanner.scan(["AOT", "PTT", "CPALL"])
    # Results should be sorted by score descending
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_multi_market_scanner():
    adapter1 = MockAdapter({"AOT": Quote(symbol="AOT", last=thb(50), timestamp=datetime.now())})
    adapter2 = MockAdapter({"BTC/USDT": Quote(symbol="BTC/USDT", last=thb(2000000), timestamp=datetime.now())})

    scanner1 = MarketScanner(adapter1)
    scanner2 = MarketScanner(adapter2)

    multi = MultiMarketScanner()
    multi.add_scanner("equity", scanner1)
    multi.add_scanner("crypto", scanner2)

    results = await multi.scan_all({"equity": ["AOT"], "crypto": ["BTC/USDT"]})
    assert "equity" in results
    assert "crypto" in results
    assert len(results["equity"]) == 1
    assert len(results["crypto"]) == 1