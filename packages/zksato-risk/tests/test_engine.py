"""Tests for zksato-risk engine."""

import pytest
from zksato_risk.engine import RiskEngine
from zksato_core.models import OrderIntent, RiskContext, Side, OrderType
from zksato_core.money import thb
from zksato_core.config import BaseConfig


class MockSettings(BaseConfig):
    kill_switch: bool = False
    account_allowed: bool = True
    market_data_available: bool = True
    market_session_known: bool = True
    market_session_open: bool = True
    price_band_ok: bool = True
    tick_size_ok: bool = True
    allow_equity_short_selling: bool = False
    strict_reference_data: bool = False
    max_daily_loss_pct: float = 2.0
    max_drawdown_pct: float = 5.0
    max_positions: int = 5
    max_position_pct: float = 10.0
    max_orders_per_day: int = 50
    max_open_orders: int = 20
    max_gross_exposure_pct: float = 80.0
    max_net_exposure_pct: float = 80.0
    max_symbol_exposure_pct: float = 20.0
    max_sector_exposure_pct: float = 35.0
    market_data_stale_seconds: float = 10.0
    max_spread_pct: float = 3.0
    max_notional_per_order: float = 100_000.0
    require_stop_loss: bool = True
    max_price_deviation_pct: float = 10.0
    max_risk_per_trade_pct: float = 0.5
    prediction_max_order_usd: float = 10.0
    max_directional_residual: float = 100.0
    max_complete_set_cost: float = 1.0
    min_prediction_edge: float = 0.03


def test_risk_engine_buy_approved():
    settings = MockSettings()
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        stop_loss=thb(48),
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
        current_positions=0,
        daily_pnl_pct=0.0,
        drawdown_pct=0.0,
        position_pct_after_trade=5.0,
        orders_today=0,
        open_orders=0,
        gross_exposure_pct=0.0,
        net_exposure_pct=0.0,
        symbol_exposure_pct=0.0,
        sector_exposure_pct=0.0,
        quote_age_seconds=1.0,
        spread_pct=0.5,
        market_session_known=True,
        market_session_open=True,
        market_data_available=True,
        price_band_ok=True,
        tick_size_ok=True,
        account_allowed=True,
        opens_new_position=True,
        reduces_exposure=False,
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is True
    assert len(decision.reasons) == 0


def test_risk_engine_kill_switch():
    settings = MockSettings(kill_switch=True)
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        stop_loss=thb(48),
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "global kill switch is active" in decision.reasons


def test_risk_engine_account_not_allowed():
    settings = MockSettings()
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        stop_loss=thb(48),
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
        account_allowed=False,
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "account is not in the configured trading allow-list" in decision.reasons


def test_risk_engine_stale_quote():
    settings = MockSettings(market_data_stale_seconds=5.0)
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        stop_loss=thb(48),
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
        quote_age_seconds=10.0,
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "market quote is stale" in decision.reasons


def test_risk_engine_no_stop_loss():
    settings = MockSettings(require_stop_loss=True)
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        # No stop_loss
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "stop loss is required for buy orders" in decision.reasons


def test_risk_engine_sell_exceeds_position():
    settings = MockSettings(allow_equity_short_selling=False)
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.SELL,
        quantity=200,
        order_type=OrderType.LIMIT,
        price=thb(50),
    )
    context = RiskContext(
        reference_price=thb(50),
        available_quantity=100,
        reduces_exposure=False,
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "sell quantity exceeds available position" in decision.reasons


def test_risk_engine_max_positions():
    settings = MockSettings(max_positions=2)
    engine = RiskEngine(settings)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=thb(50),
        stop_loss=thb(48),
    )
    context = RiskContext(
        reference_price=thb(50),
        portfolio_value=thb(100_000),
        current_positions=2,
        opens_new_position=True,
    )

    decision = engine.evaluate(intent, context)
    assert decision.approved is False
    assert "maximum number of positions reached" in decision.reasons