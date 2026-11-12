"""zksato-market: Market data, feeds, and adapters for zksato trading platform."""

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

from zksato_market.feeds import (
    Feed,
    MarketDataFeed,
    FeedMetrics,
    CompositeFeed,
    FeedEvent,
    SettradeFeed,
    SettradeRealtimeFeed,
    CCXTFeed,
    BinanceFeed,
    BinanceTHFeed,
    KuCoinFeed,
    OKXFeed,
    BybitFeed,
    MultiFeed,
    ReplayFeed,
    ReplayEvent,
)

from zksato_market.adapters import (
    MarketDataAdapter,
    RESTAdapter,
    SettradeAdapter,
    CCXTAdapter,
)

from zksato_market.reference import ReferenceData, get_reference_data, load_reference_data
from zksato_market.calendar import TradingCalendar
from zksato_market.scanner import MarketScanner, MultiMarketScanner, ScanFilter

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
    "FeedEvent",
    "SettradeFeed",
    "SettradeRealtimeFeed",
    "CCXTFeed",
    "BinanceFeed",
    "BinanceTHFeed",
    "KuCoinFeed",
    "OKXFeed",
    "BybitFeed",
    "MultiFeed",
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