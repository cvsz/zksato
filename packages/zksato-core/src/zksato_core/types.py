"""Shared enums, type aliases, and constants."""

from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"
    UP = "up"
    DOWN = "down"


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    NEEDS_RECONCILIATION = "needs_reconciliation"


class SignalAction(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class BotState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class TradingMode(StrEnum):
    PAPER = "paper"
    SANDBOX = "sandbox"
    LIVE = "live"


# Type aliases
OrderId = str
ClientOrderId = str
BrokerOrderId = str
FillId = str
Symbol = str
CorrelationId = str
Timestamp = str  # ISO 8601 format
