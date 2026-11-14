"""zksato-market: Market data, feeds, adapters, and technical indicators for zksato trading platform."""

from zksato_market.adapters import (
    CCXTAdapter,
    MarketDataAdapter,
    RESTAdapter,
    SettradeAdapter,
)
from zksato_market.calendar import TradingCalendar
from zksato_market.features import build_market_features
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
    "Feed",
    "FeedConfig",
    "FeedEvent",
    "FeedMetrics",
    "FeedRouter",
    "FeedStatus",
    "Instrument",
    "KuCoinFeed",
    "MarketDataAdapter",
    "MarketDataFeed",
    "MarketScanner",
    "MarketType",
    "MultiFeed",
    "MultiMarketScanner",
    "OKXFeed",
    "Quote",
    "RESTAdapter",
    "ReferenceData",
    "ReplayEvent",
    "ReplayFeed",
    "ScanFilter",
    "SettradeAdapter",
    "SettradeFeed",
    "SettradeRealtimeFeed",
    "Trade",
    "TradingCalendar",
    "build_market_features",
    "get_reference_data",
    "load_reference_data",
]
