"""zksato-market: Market data, feeds, and adapters for zksato trading platform."""

from zksato_market.adapters import (
    CCXTAdapter,
    MarketDataAdapter,
    RESTAdapter,
    SettradeAdapter,
)
from zksato_market.calendar import TradingCalendar
from zksato_market.feeds import (
    BinanceFeed,
    BinanceTHFeed,
    BybitFeed,
    CCXTFeed,
    CompositeFeed,
    Feed,
    FeedMetrics,
    FeedRouter,
    KuCoinFeed,
    MarketDataFeed,
    MultiFeed,
    OKXFeed,
    ReplayEvent,
    ReplayFeed,
    SettradeFeed,
    SettradeRealtimeFeed,
)
from zksato_market.reference import ReferenceData, get_reference_data, load_reference_data
from zksato_market.scanner import MarketScanner, MultiMarketScanner, ScanFilter
from zksato_market.types import (
    Bar,
    FeedConfig,
    FeedEvent,
    FeedStatus,
    Instrument,
    MarketType,
    Quote,
    Trade,
)

__version__ = "2.0.0-dev"

__all__ = [
    "Bar",
    "BinanceFeed",
    "BinanceTHFeed",
    "BybitFeed",
    "CCXTAdapter",
    "CCXTFeed",
    "CompositeFeed",
    # Feeds
    "Feed",
    "FeedConfig",
    "FeedEvent",
    "FeedMetrics",
    "FeedRouter",
    "FeedStatus",
    "Instrument",
    "KuCoinFeed",
    # Adapters
    "MarketDataAdapter",
    "MarketDataFeed",
    # Scanner
    "MarketScanner",
    # Types
    "MarketType",
    "MultiFeed",
    "MultiMarketScanner",
    "OKXFeed",
    "Quote",
    "RESTAdapter",
    # Reference
    "ReferenceData",
    "ReplayEvent",
    "ReplayFeed",
    "ScanFilter",
    "SettradeAdapter",
    "SettradeFeed",
    "SettradeRealtimeFeed",
    "Trade",
    # Calendar
    "TradingCalendar",
    "get_reference_data",
    "load_reference_data",
]
