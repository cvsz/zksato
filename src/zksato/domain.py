from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


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


class Bar(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(default="1m", min_length=1, max_length=16)
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(default=0, ge=0)
    value: float = Field(default=0, ge=0)
    source: str = Field(default="unknown", min_length=1, max_length=64)

    @field_validator("symbol")
    @classmethod
    def normalize_bar_symbol(cls, value: str) -> str:
        return value.strip().upper()


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
    available_quantity: int | None = Field(default=None, ge=0)
    reference_price: float | None = Field(default=None, gt=0)
    orders_today: int = Field(default=0, ge=0)
    open_orders: int = Field(default=0, ge=0)
    portfolio_value: float | None = Field(default=None, gt=0)
    gross_exposure_pct: float = Field(default=0.0, ge=0)
    net_exposure_pct: float = 0.0
    symbol_exposure_pct: float = Field(default=0.0, ge=0)
    sector_exposure_pct: float = Field(default=0.0, ge=0)
    quote_age_seconds: float | None = Field(default=None, ge=0)
    spread_pct: float | None = Field(default=None, ge=0)
    market_session_known: bool = True
    market_session_open: bool = True
    market_data_available: bool = True
    price_band_ok: bool = True
    tick_size_ok: bool = True
    account_allowed: bool = True
    opens_new_position: bool = True
    reduces_exposure: bool = False
    prediction_directional_residual: float | None = Field(default=None, ge=0)
    prediction_complete_set_cost: float | None = Field(default=None, ge=0)
    prediction_edge: float | None = Field(default=None)


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
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrderEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    event_type: str = Field(min_length=1, max_length=64)
    status: OrderStatus | None = None
    data: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FillRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    broker_fill_id: str | None = Field(default=None, max_length=128)
    order_id: UUID | None = None
    broker_order_id: str | None = Field(default=None, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0.0, ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("symbol")
    @classmethod
    def normalize_fill_symbol(cls, value: str) -> str:
        return value.strip().upper()


class RiskEvaluation(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    client_order_id: str | None = Field(default=None, max_length=128)
    symbol: str = Field(min_length=1, max_length=32)
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    inputs: dict[str, object] = Field(default_factory=dict)
    estimated_notional: float = 0.0
    estimated_risk_pct: float | None = None
    policy_version: str = Field(default="v1", min_length=1, max_length=64)
    actor: str = Field(default="system", min_length=1, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class AccountSnapshot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    cash: float
    market_value: float
    equity: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    daily_pnl: float = 0.0
    source: str = Field(default="local", min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyConfig(BaseModel):
    name: str = "ema_cross"
    fast_period: int = Field(default=5, ge=2, le=200)
    slow_period: int = Field(default=20, ge=3, le=500)
    signal_period: int = Field(default=9, ge=2, le=200)
    rsi_period: int = Field(default=14, ge=2, le=100)
    rsi_buy: float = Field(default=30, ge=1, le=50)
    rsi_sell: float = Field(default=70, ge=50, le=99)
    breakout_period: int = Field(default=20, ge=2, le=500)
    bollinger_period: int = Field(default=20, ge=2, le=500)
    bollinger_deviations: float = Field(default=2.0, gt=0, le=10)
    momentum_period: int = Field(default=10, ge=1, le=500)
    momentum_threshold_pct: float = Field(default=1.0, ge=0, le=100)
    sentiment_buy_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    sentiment_sell_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    min_history: int = Field(default=25, ge=3, le=1000)
    vwap_period: int = Field(default=14, ge=1, le=500)
    scalp_fast_period: int = Field(default=3, ge=2, le=200)
    scalp_slow_period: int = Field(default=8, ge=3, le=500)
    swing_rsi_period: int = Field(default=14, ge=2, le=100)
    position_fast_period: int = Field(default=50, ge=2, le=500)
    position_slow_period: int = Field(default=200, ge=3, le=1000)
    stoch_k_period: int = Field(default=14, ge=2, le=200)
    stoch_d_period: int = Field(default=3, ge=1, le=50)
    stoch_overbought: float = Field(default=80.0, ge=50.0, le=100.0)
    stoch_oversold: float = Field(default=20.0, ge=0.0, le=50.0)
    atr_period: int = Field(default=14, ge=2, le=200)
    atr_multiplier: float = Field(default=1.5, ge=0.1, le=10.0)
    williams_r_period: int = Field(default=14, ge=2, le=200)
    williams_r_overbought: float = Field(default=-20.0, ge=-50.0, le=0.0)
    williams_r_oversold: float = Field(default=-80.0, ge=-100.0, le=-50.0)


class StrategyVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    config: dict[str, object] = Field(default_factory=dict)
    code_hash: str = Field(min_length=8, max_length=128)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    strategy_version_id: UUID | None = None
    strategy: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    mode: str = Field(default="research", min_length=1, max_length=32)
    inputs: dict[str, object] = Field(default_factory=dict)
    output: dict[str, object] = Field(default_factory=dict)
    evidence_hash: str | None = Field(default=None, min_length=64, max_length=64)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


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
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    max_signals_per_tick: int = Field(default=0, ge=0, le=100)

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
    slippage_pct: float = Field(default=0.05, ge=0, le=5)


class BacktestTrade(BaseModel):
    side: Side
    timestamp: datetime
    price: float
    quantity: int
    pnl: float = 0.0
    fee: float = Field(default=0.0, ge=0)


class BacktestResult(BaseModel):
    symbol: str
    initial_cash: float
    final_equity: float
    total_return_pct: float
    max_drawdown_pct: float
    total_trades: int
    win_rate_pct: float
    closed_trades: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float | None = None
    average_closed_trade_pnl: float = 0.0
    fees_paid: float = 0.0
    exposure_pct: float = 0.0
    buy_and_hold_return_pct: float = 0.0
    trades: list[BacktestTrade] = Field(default_factory=list)
    equity_curve: list[float] = Field(default_factory=list)
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None


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
    previous_hash: str | None = None
    event_hash: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OutboxMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    topic: str
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = None


class ReconciliationReport(BaseModel):
    examined_remote: int = 0
    inserted: int = 0
    updated: int = 0
    marked_unknown: int = 0
    fills_recorded: int = 0
    positions_checked: int = 0
    unresolved_order_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScannerResult(BaseModel):
    symbol: str
    last: float
    change_pct: float
    volume: float
    score: float
    reasons: list[str] = Field(default_factory=list)


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
