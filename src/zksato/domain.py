from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


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


class SignalAction(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class BotState(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class Quote(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    last: float = Field(gt=0)
    bid: float | None = Field(default=None, gt=0)
    offer: float | None = Field(default=None, gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)
    open: float | None = Field(default=None, gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    volume: float = Field(default=0, ge=0)
    value: float = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @property
    def change_pct(self) -> float:
        if not self.previous_close:
            return 0.0
        return ((self.last - self.previous_close) / self.previous_close) * 100


class Candle(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(default=0, ge=0)


class OrderIntent(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: int = Field(gt=0)
    order_type: OrderType = OrderType.LIMIT
    price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    client_order_id: str | None = Field(default=None, min_length=1, max_length=128)
    source: str = Field(default="manual", min_length=1, max_length=64)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_price(self) -> OrderIntent:
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for limit orders")
        return self


class RiskContext(BaseModel):
    current_positions: int = Field(default=0, ge=0)
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = Field(default=0.0, ge=0)
    position_pct_after_trade: float = Field(default=0.0, ge=0, le=100)
    line_available: float | None = Field(default=None, ge=0)
    reference_price: float | None = Field(default=None, gt=0)
    orders_today: int = Field(default=0, ge=0)
    portfolio_value: float | None = Field(default=None, gt=0)


class OrderSubmission(BaseModel):
    intent: OrderIntent
    risk: RiskContext = Field(default_factory=RiskContext)
    confirmation_token: str | None = None


class RiskDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    estimated_notional: float = 0.0
    estimated_risk_pct: float | None = None


class OrderRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    broker_order_id: str | None = None
    client_order_id: str | None = None
    symbol: str
    side: Side
    quantity: int
    filled_quantity: int = 0
    order_type: OrderType
    price: float | None
    average_fill_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    status: OrderStatus
    source: str = "manual"
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Position(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    market_price: float
    market_value: float
    cost_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioSnapshot(BaseModel):
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float
    positions: list[Position] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyConfig(BaseModel):
    name: str = "ema_cross"
    fast_period: int = Field(default=5, ge=2, le=200)
    slow_period: int = Field(default=20, ge=3, le=500)
    rsi_period: int = Field(default=14, ge=2, le=100)
    rsi_buy: float = Field(default=30, ge=1, le=50)
    rsi_sell: float = Field(default=70, ge=50, le=99)
    breakout_period: int = Field(default=20, ge=2, le=500)
    min_history: int = Field(default=25, ge=3, le=1000)


class Signal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    symbol: str
    strategy: str
    action: SignalAction
    price: float
    confidence: float = Field(default=0.5, ge=0, le=1)
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BotConfig(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    order_size: int = Field(default=100, ge=1)
    stop_loss_pct: float = Field(default=2.0, gt=0, le=50)
    take_profit_pct: float = Field(default=4.0, gt=0, le=100)
    auto_execute: bool = True
    cooldown_seconds: int = Field(default=60, ge=0, le=86_400)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        return sorted({item.strip().upper() for item in value if item.strip()})


class BotStatus(BaseModel):
    state: BotState = BotState.STOPPED
    config: BotConfig | None = None
    last_tick_at: datetime | None = None
    signals_generated: int = 0
    orders_submitted: int = 0
    last_error: str | None = None


class BacktestRequest(BaseModel):
    symbol: str
    candles: list[Candle] = Field(min_length=5)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    initial_cash: float = Field(default=100_000.0, gt=0)
    order_size: int = Field(default=100, ge=1)
    commission_pct: float = Field(default=0.15, ge=0, le=5)


class BacktestTrade(BaseModel):
    side: Side
    timestamp: datetime
    price: float
    quantity: int
    pnl: float = 0.0


class BacktestResult(BaseModel):
    symbol: str
    initial_cash: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    total_trades: int
    win_rate_pct: float
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[float] = Field(default_factory=list)


class AlertRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    symbol: str
    operator: str = Field(pattern="^(gte|lte)$")
    price: float = Field(gt=0)
    enabled: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_alert_symbol(cls, value: str) -> str:
        return value.strip().upper()


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    message: str
    data: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DashboardSnapshot(BaseModel):
    mode: str
    automation_enabled: bool
    kill_switch: bool
    bot: BotStatus
    portfolio: PortfolioSnapshot
    quotes: list[Quote]
    orders: list[OrderRecord]
    signals: list[Signal]
    alerts: list[AlertRule]
    audit: list[AuditEvent]
