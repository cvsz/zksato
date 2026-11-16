"""Core domain models: orders, fills, positions, accounts, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from zksato_core.ids import new_correlation_id
from zksato_core.money import Money, thb
from zksato_core.types import BotState, OrderStatus, OrderType, Side, SignalAction


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
    value: Money = field(default_factory=lambda: thb(0))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

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
class Candle:
    """OHLCV candle."""

    timestamp: datetime
    open: Money
    high: Money
    low: Money
    close: Money
    volume: int = 0


@dataclass(frozen=True, slots=True)
class Trade:
    """Market trade."""

    symbol: str
    price: Money
    quantity: int
    side: Side
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    trade_id: str | None = None
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class Bar:
    """Persisted bar with metadata."""

    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    timeframe: str = "1m"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    open: Money = field(default_factory=lambda: thb(0))
    high: Money = field(default_factory=lambda: thb(0))
    low: Money = field(default_factory=lambda: thb(0))
    close: Money = field(default_factory=lambda: thb(0))
    volume: int = 0
    value: Money = field(default_factory=lambda: thb(0))
    source: str = "unknown"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Intent to place an order."""

    symbol: str
    side: Side
    quantity: int
    order_type: OrderType = OrderType.LIMIT
    price: Money | None = None
    stop_loss: Money | None = None
    take_profit: Money | None = None
    client_order_id: str | None = None
    source: str = "manual"

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for limit orders")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Risk evaluation context."""

    current_positions: int = 0
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    position_pct_after_trade: float = 0.0
    line_available: Money | None = None
    available_quantity: int | None = None
    reference_price: Money | None = None
    orders_today: int = 0
    open_orders: int = 0
    portfolio_value: Money | None = None
    gross_exposure_pct: float = 0.0
    net_exposure_pct: float = 0.0
    symbol_exposure_pct: float = 0.0
    sector_exposure_pct: float = 0.0
    quote_age_seconds: float | None = None
    spread_pct: float | None = None
    market_session_known: bool = True
    market_session_open: bool = True
    market_data_available: bool = True
    price_band_ok: bool = True
    tick_size_ok: bool = True
    account_allowed: bool = True
    opens_new_position: bool = True
    reduces_exposure: bool = False
    prediction_directional_residual: float | None = None
    prediction_complete_set_cost: float | None = None
    prediction_edge: float | None = None


@dataclass(frozen=True, slots=True)
class OrderSubmission:
    """Order submission with risk context."""

    intent: OrderIntent
    risk: RiskContext = field(default_factory=RiskContext)
    confirmation_token: str | None = None


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Risk evaluation decision."""

    approved: bool
    reasons: list[str] = field(default_factory=list)
    estimated_notional: Money = field(default_factory=lambda: thb(0))
    estimated_risk_pct: float | None = None


@dataclass(frozen=True, slots=True)
class OrderRecord:
    """Persisted order record."""

    id: UUID = field(default_factory=uuid4)
    broker_order_id: str | None = None
    client_order_id: str | None = None
    symbol: str = ""
    side: Side = Side.BUY
    quantity: int = 0
    filled_quantity: int = 0
    order_type: OrderType = OrderType.LIMIT
    price: Money | None = None
    average_fill_price: Money | None = None
    stop_loss: Money | None = None
    take_profit: Money | None = None
    status: OrderStatus = OrderStatus.PENDING
    source: str = "manual"
    message: str | None = None
    correlation_id: str = field(default_factory=new_correlation_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_open(self) -> bool:
        return self.status in {
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
        }

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.NEEDS_RECONCILIATION,
        }


@dataclass(frozen=True, slots=True)
class OrderEvent:
    """Order lifecycle event."""

    id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    status: OrderStatus | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class FillRecord:
    """Persisted fill record."""

    id: UUID = field(default_factory=uuid4)
    broker_fill_id: str | None = None
    order_id: UUID | None = None
    broker_order_id: str | None = None
    symbol: str = ""
    side: Side = Side.BUY
    quantity: int = 0
    price: Money = field(default_factory=lambda: thb(0))
    fee: Money = field(default_factory=lambda: thb(0))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def notional(self) -> Money:
        return self.price * self.quantity


@dataclass(frozen=True, slots=True)
class RiskEvaluation:
    """Persisted risk evaluation."""

    id: UUID = field(default_factory=uuid4)
    client_order_id: str | None = None
    symbol: str = ""
    approved: bool = False
    reasons: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    estimated_notional: Money = field(default_factory=lambda: thb(0))
    estimated_risk_pct: float | None = None
    policy_version: str = "v1"
    actor: str = "system"
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class Position:
    """Position in a symbol."""

    symbol: str
    quantity: int
    average_price: Money
    market_price: Money
    market_value: Money
    cost_value: Money
    unrealized_pnl: Money
    unrealized_pnl_pct: float


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Portfolio snapshot."""

    cash: Money
    market_value: Money
    equity: Money
    realized_pnl: Money
    unrealized_pnl: Money
    daily_pnl: Money
    positions: list[Position] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Account snapshot from broker."""

    id: UUID = field(default_factory=uuid4)
    cash: Money = field(default_factory=lambda: thb(0))
    market_value: Money = field(default_factory=lambda: thb(0))
    equity: Money = field(default_factory=lambda: thb(0))
    realized_pnl: Money = field(default_factory=lambda: thb(0))
    unrealized_pnl: Money = field(default_factory=lambda: thb(0))
    daily_pnl: Money = field(default_factory=lambda: thb(0))
    source: str = "local"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Strategy configuration."""

    name: str = "ema_cross"
    fast_period: int = 5
    slow_period: int = 20
    signal_period: int = 9
    rsi_period: int = 14
    rsi_buy: float = 30
    rsi_sell: float = 70
    breakout_period: int = 20
    bollinger_period: int = 20
    bollinger_deviations: float = 2.0
    momentum_period: int = 10
    momentum_threshold_pct: float = 1.0
    sentiment_buy_threshold: float = 0.8
    sentiment_sell_threshold: float = 0.2
    min_history: int = 25
    vwap_period: int = 14
    scalp_fast_period: int = 3
    scalp_slow_period: int = 8
    swing_rsi_period: int = 14
    position_fast_period: int = 50
    position_slow_period: int = 200
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    stoch_overbought: float = 80.0
    stoch_oversold: float = 20.0
    atr_period: int = 14
    atr_multiplier: float = 1.5
    williams_r_period: int = 14
    williams_r_overbought: float = -20.0
    williams_r_oversold: float = -80.0
    stat_arb_period: int = 20
    stat_arb_zscore_entry: float = 2.0
    stat_arb_zscore_exit: float = 0.5
    tfex_spread_threshold: float = 2.0


@dataclass(frozen=True, slots=True)
class StrategyVersion:
    """Strategy version with code hash."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    version: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    code_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class StrategyRun:
    """Strategy execution run."""

    id: UUID = field(default_factory=uuid4)
    strategy_version_id: UUID | None = None
    strategy: str = ""
    symbol: str = ""
    mode: str = "research"
    inputs: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    evidence_hash: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Signal:
    """Trading signal."""

    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    strategy: str = ""
    action: SignalAction = SignalAction.HOLD
    price: Money = field(default_factory=lambda: thb(0))
    confidence: float = 0.5
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Bot configuration."""

    symbols: list[str] = field(default_factory=list)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    order_size: int = 100
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 4.0
    auto_execute: bool = True
    cooldown_seconds: int = 60
    confidence_threshold: float = 0.0
    max_signals_per_tick: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "symbols",
            sorted({s.strip().upper() for s in self.symbols if s.strip()}),
        )


@dataclass(frozen=True, slots=True)
class BotStatus:
    """Bot status."""

    state: BotState = BotState.STOPPED
    config: BotConfig | None = None
    last_tick_at: datetime | None = None
    signals_generated: int = 0
    orders_submitted: int = 0
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestRequest:
    """Backtest request."""

    symbol: str = ""
    candles: list[Candle] = field(default_factory=list)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    initial_cash: Money = field(default_factory=lambda: thb(100_000))
    order_size: int = 100
    commission_pct: float = 0.15
    slippage_pct: float = 0.05


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    """Backtest trade."""

    side: Side
    timestamp: datetime
    price: Money
    quantity: int
    pnl: Money = field(default_factory=lambda: thb(0))
    fee: Money = field(default_factory=lambda: thb(0))


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Backtest result."""

    symbol: str
    initial_cash: Money
    final_equity: Money
    total_return_pct: float
    max_drawdown_pct: float
    total_trades: int
    win_rate_pct: float
    closed_trades: int = 0
    gross_profit: Money = field(default_factory=lambda: thb(0))
    gross_loss: Money = field(default_factory=lambda: thb(0))
    profit_factor: float | None = None
    average_closed_trade_pnl: Money = field(default_factory=lambda: thb(0))
    fees_paid: Money = field(default_factory=lambda: thb(0))
    exposure_pct: float = 0.0
    buy_and_hold_return_pct: float = 0.0
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class AlertRule:
    """Price alert rule."""

    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    operator: str = "gte"  # gte or lte
    price: Money = field(default_factory=lambda: thb(0))
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.strip().upper())


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Audit log event."""

    id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    previous_hash: str | None = None
    event_hash: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class OutboxMessage:
    """Outbox message for reliable delivery."""

    id: UUID = field(default_factory=uuid4)
    topic: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    sent_at: datetime | None = None
    retry_count: int = 0
    last_error: str | None = None
    last_attempt_at: datetime | None = None
    dead_lettered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    """Reconciliation report."""

    examined_remote: int = 0
    inserted: int = 0
    updated: int = 0
    marked_unknown: int = 0
    fills_recorded: int = 0
    positions_checked: int = 0
    divergence_count: int = 0
    divergences: list[dict[str, Any]] = field(default_factory=list)
    unresolved_order_ids: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ScannerResult:
    """Market scanner result."""

    symbol: str = ""
    last: Money = field(default_factory=lambda: thb(0))
    change_pct: float = 0.0
    volume: int = 0
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Dashboard data snapshot."""

    mode: str = "paper"
    automation_enabled: bool = True
    kill_switch: bool = False
    bot: BotStatus = field(default_factory=BotStatus)
    portfolio: PortfolioSnapshot = field(
        default_factory=lambda: PortfolioSnapshot(
            cash=thb(0),
            market_value=thb(0),
            equity=thb(0),
            realized_pnl=thb(0),
            unrealized_pnl=thb(0),
            daily_pnl=thb(0),
        )
    )
    quotes: list[Quote] = field(default_factory=list)
    orders: list[OrderRecord] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    alerts: list[AlertRule] = field(default_factory=list)
    audit: list[AuditEvent] = field(default_factory=list)
