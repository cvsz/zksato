"""Market data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from zksato_core.money import Money


class MarketType(StrEnum):
    EQUITY = "equity"
    TFEX = "tfex"
    CRYPTO = "crypto"
    PREDICTION = "prediction"


class FeedStatus(StrEnum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass(frozen=True, slots=True)
class Quote:
    """Market quote."""

    symbol: str
    last: Money
    bid: Money | None = None
    offer: Money | None = None
    high: Money | None = None
    low: Money | None = None
    open: Money | None = None
    previous_close: Money | None = None
    volume: int = 0
    value: Money = field(default_factory=lambda: Money(0))
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"

    @property
    def change_pct(self) -> float:
        if not self.previous_close or self.previous_close.amount == 0:
            return 0.0
        return float(
            (self.last.amount - self.previous_close.amount) / self.previous_close.amount * 100
        )

    @property
    def spread(self) -> Money | None:
        if self.bid and self.offer:
            return self.offer - self.bid
        return None

    @property
    def spread_pct(self) -> float | None:
        if self.spread and self.last.amount > 0:
            return float(self.spread.amount / self.last.amount * 100)
        return None


@dataclass(frozen=True, slots=True)
class Trade:
    """Market trade."""

    symbol: str
    price: Money
    quantity: int
    side: str  # "buy" or "sell"
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str | None = None
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class Bar:
    """OHLCV bar."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: Money
    high: Money
    low: Money
    close: Money
    volume: int = 0
    value: Money = field(default_factory=lambda: Money(0))
    source: str = "unknown"
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Instrument:
    """Instrument reference data."""

    symbol: str
    name: str
    market_type: MarketType
    tick_size: Money
    board_lot: int = 100
    price_band_pct: float | None = None
    sector: str | None = None
    is_tradable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FeedEvent:
    """Feed event."""

    event_type: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class FeedConfig:
    """Feed configuration."""

    name: str
    market_type: MarketType
    symbols: list[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    config: dict[str, Any] = field(default_factory=dict)
