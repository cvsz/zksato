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
    FeedEvent,
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
    # Types
    "MarketType",
    "FeedStatus",
    "Quote",
    "Trade",
    "Bar",
    "Instrument",
    "FeedEvent",
    "FeedConfig",
    # Feeds
    "Feed",
    "MarketDataFeed",
    "FeedMetrics",
    "CompositeFeed",
    "SettradeFeed",
    "SettradeRealtimeFeed",
    "CCXTFeed",
    "BinanceFeed",
    "BinanceTHFeed",
    "KuCoinFeed",
    "OKXFeed",
    "BybitFeed",
    "MultiFeed",
    "FeedRouter",
    "ReplayFeed",
    "ReplayEvent",
    # Adapters
    "MarketDataAdapter",
    "RESTAdapter",
    "SettradeAdapter",
    "CCXTAdapter",
    # Reference
    "ReferenceData",
    "get_reference_data",
    "load_reference_data",
    # Calendar
    "TradingCalendar",
    # Scanner
    "MarketScanner",
    "MultiMarketScanner",
    "ScanFilter",
]
