"""Tests for zksato-core models module."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from zksato_core.models import (
    AccountSnapshot,
    AlertRule,
    AuditEvent,
    BacktestRequest,
    BacktestResult,
    BacktestTrade,
    Bar,
    BotConfig,
    BotStatus,
    Candle,
    DashboardSnapshot,
    FillRecord,
    OrderEvent,
    OrderIntent,
    OrderRecord,
    OrderSubmission,
    OutboxMessage,
    PortfolioSnapshot,
    Position,
    Quote,
    ReconciliationReport,
    RiskContext,
    RiskDecision,
    ScannerResult,
    Signal,
    StrategyConfig,
    StrategyVersion,
)
from zksato_core.money import thb
from zksato_core.types import BotState, OrderStatus, OrderType, Side, SignalAction


def test_quote():
    quote = Quote(
        symbol="AOT",
        last=thb(50),
        bid=thb(49.50),
        offer=thb(50.50),
        high=thb(52),
        low=thb(48),
        open=thb(49),
        previous_close=thb(48.50),
        volume=10000,
        value=thb(500000),
    )
    assert quote.symbol == "AOT"
    assert quote.change_pct == pytest.approx(3.09, rel=0.01)
    assert quote.spread == thb(1.0)
    assert quote.spread_pct == pytest.approx(2.0, rel=0.01)


def test_candle():
    candle = Candle(
        timestamp=datetime.now(UTC),
        open=thb(49),
        high=thb(52),
        low=thb(48),
        close=thb(50),
        volume=10000,
    )
    assert candle.close == thb(50)


def test_bar():
    bar = Bar(
        symbol="AOT",
        timeframe="1m",
        timestamp=datetime.now(UTC),
        open=thb(49),
        high=thb(52),
        low=thb(48),
        close=thb(50),
        volume=10000,
        value=thb(500000),
        source="settrade",
    )
    assert bar.symbol == "AOT"
    assert bar.source == "settrade"


def test_order_intent():
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
    )
    assert intent.symbol == "AOT"
    assert intent.side == Side.BUY
    assert intent.quantity == 100
    assert intent.price == thb(50)


def test_order_intent_market():
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.MARKET,
    )
    assert intent.order_type == OrderType.MARKET
    assert intent.price is None


def test_order_intent_limit_requires_price():
    with pytest.raises(ValueError, match="price is required for limit orders"):
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
        )


def test_order_intent_positive_quantity():
    with pytest.raises(ValueError, match="quantity must be positive"):
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=0,
            order_type=OrderType.LIMIT,
            price=thb(50),
        )


def test_risk_context():
    ctx = RiskContext(
        current_positions=3,
        daily_pnl_pct=-1.0,
        drawdown_pct=2.0,
        portfolio_value=thb(100000),
    )
    assert ctx.current_positions == 3
    assert ctx.portfolio_value == thb(100000)


def test_order_submission():
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
    )
    ctx = RiskContext(portfolio_value=thb(100000))
    submission = OrderSubmission(intent=intent, risk=ctx)
    assert submission.intent == intent
    assert submission.risk == ctx


def test_risk_decision():
    decision = RiskDecision(
        approved=True,
        reasons=[],
        estimated_notional=thb(5000),
        estimated_risk_pct=0.5,
    )
    assert decision.approved is True
    assert decision.estimated_notional == thb(5000)


def test_risk_decision_rejected():
    decision = RiskDecision(
        approved=False,
        reasons=["daily loss limit reached"],
        estimated_notional=thb(5000),
    )
    assert decision.approved is False
    assert len(decision.reasons) == 1


def test_order_record():
    order = OrderRecord(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        status=OrderStatus.ACCEPTED,
    )
    assert order.symbol == "AOT"
    assert order.remaining_quantity == 100
    assert order.is_open is True
    assert order.is_terminal is False


def test_order_record_filled():
    order = OrderRecord(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        filled_quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        status=OrderStatus.FILLED,
    )
    assert order.remaining_quantity == 0
    assert order.is_open is False
    assert order.is_terminal is True


def test_order_event():
    event = OrderEvent(
        order_id=uuid4(),
        event_type="order.accepted",
        status=OrderStatus.ACCEPTED,
        data={"broker_order_id": "123"},
    )
    assert event.event_type == "order.accepted"
    assert event.status == OrderStatus.ACCEPTED


def test_fill_record():
    fill = FillRecord(
        order_id=uuid4(),
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        price=thb(50),
        fee=thb(7.5),
    )
    assert fill.notional == thb(5000)
    assert fill.fee == thb(7.5)


def test_position():
    pos = Position(
        symbol="AOT",
        quantity=100,
        average_price=thb(48),
        market_price=thb(50),
        market_value=thb(5000),
        cost_value=thb(4800),
        unrealized_pnl=thb(200),
        unrealized_pnl_pct=4.17,
    )
    assert pos.symbol == "AOT"
    assert pos.quantity == 100


def test_portfolio_snapshot():
    portfolio = PortfolioSnapshot(
        cash=thb(50000),
        market_value=thb(50000),
        equity=thb(100000),
        realized_pnl=thb(1000),
        unrealized_pnl=thb(200),
        daily_pnl=thb(500),
    )
    assert portfolio.equity == thb(100000)


def test_account_snapshot():
    snapshot = AccountSnapshot(
        cash=thb(50000),
        market_value=thb(50000),
        equity=thb(100000),
        source="settrade",
    )
    assert snapshot.source == "settrade"


def test_strategy_config():
    config = StrategyConfig(
        name="ema_cross",
        fast_period=5,
        slow_period=20,
    )
    assert config.name == "ema_cross"
    assert config.fast_period == 5
    assert config.slow_period == 20


def test_strategy_version():
    version = StrategyVersion(
        name="ema_cross",
        version="1.0.0",
        config={"fast_period": 5, "slow_period": 20},
        code_hash="abc123",
    )
    assert version.name == "ema_cross"
    assert version.version == "1.0.0"


def test_signal():
    signal = Signal(
        symbol="AOT",
        strategy="ema_cross",
        action=SignalAction.BUY,
        price=thb(50),
        confidence=0.8,
        reason="EMA cross up",
    )
    assert signal.action == SignalAction.BUY
    assert signal.confidence == 0.8


def test_bot_config():
    config = BotConfig(
        symbols=["AOT", "PTT"],
        order_size=200,
        stop_loss_pct=3.0,
    )
    assert config.symbols == ["AOT", "PTT"]
    assert config.order_size == 200


def test_bot_config_normalizes_symbols():
    config = BotConfig(symbols=["aot", "PTT", "aot"])
    assert config.symbols == ["AOT", "PTT"]


def test_bot_status():
    status = BotStatus(
        state=BotState.RUNNING,
        signals_generated=10,
        orders_submitted=5,
    )
    assert status.state == BotState.RUNNING
    assert status.signals_generated == 10


def test_backtest_request():
    request = BacktestRequest(
        symbol="AOT",
        candles=[],
        initial_cash=thb(100000),
    )
    assert request.symbol == "AOT"
    assert request.initial_cash == thb(100000)


def test_backtest_trade():
    trade = BacktestTrade(
        side=Side.BUY,
        timestamp=datetime.now(UTC),
        price=thb(50),
        quantity=100,
        pnl=thb(100),
        fee=thb(7.5),
    )
    assert trade.side == Side.BUY


def test_backtest_result():
    result = BacktestResult(
        symbol="AOT",
        initial_cash=thb(100000),
        final_equity=thb(110000),
        total_return_pct=10.0,
        max_drawdown_pct=5.0,
        total_trades=20,
        win_rate_pct=60.0,
    )
    assert result.total_return_pct == 10.0


def test_alert_rule():
    alert = AlertRule(
        symbol="AOT",
        operator="gte",
        price=thb(55),
    )
    assert alert.symbol == "AOT"
    assert alert.operator == "gte"
    assert alert.price == thb(55)


def test_audit_event():
    event = AuditEvent(
        event_type="order.placed",
        message="Order placed for AOT",
        data={"symbol": "AOT", "quantity": 100},
    )
    assert event.event_type == "order.placed"


def test_outbox_message():
    msg = OutboxMessage(
        topic="order.created",
        payload={"order_id": "123"},
    )
    assert msg.topic == "order.created"


def test_reconciliation_report():
    report = ReconciliationReport(
        examined_remote=10,
        inserted=2,
        updated=1,
        divergence_count=1,
        divergences=[{"type": "quantity_mismatch"}],
    )
    assert report.examined_remote == 10
    assert report.divergence_count == 1


def test_scanner_result():
    result = ScannerResult(
        symbol="AOT",
        last=thb(50),
        change_pct=2.0,
        volume=10000,
        score=0.85,
        reasons=["high volume", "price up"],
    )
    assert result.score == 0.85


def test_dashboard_snapshot():
    snapshot = DashboardSnapshot(
        mode="paper",
        automation_enabled=True,
        kill_switch=False,
    )
    assert snapshot.mode == "paper"
    assert snapshot.automation_enabled is True
