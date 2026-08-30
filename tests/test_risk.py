from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def test_buy_order_within_policy_is_approved() -> None:
    engine = RiskEngine(Settings())
    decision = engine.evaluate(
        OrderIntent(symbol="AOT", side=Side.BUY, quantity=100, price=40.0, stop_loss=38.0),
        RiskContext(
            current_positions=1,
            daily_pnl_pct=-0.2,
            drawdown_pct=1.0,
            position_pct_after_trade=5.0,
            line_available=100_000.0,
        ),
    )
    assert decision.approved is True
    assert decision.reasons == []


def test_rejects_when_daily_loss_limit_reached() -> None:
    engine = RiskEngine(Settings(max_daily_loss_pct=2.0))
    decision = engine.evaluate(
        OrderIntent(symbol="AOT", side=Side.BUY, quantity=100, price=40.0, stop_loss=38.0),
        RiskContext(daily_pnl_pct=-2.0, position_pct_after_trade=5.0),
    )
    assert decision.approved is False
    assert "maximum daily loss threshold reached" in decision.reasons


def test_rejects_buy_without_stop_loss() -> None:
    engine = RiskEngine(Settings(require_stop_loss=True))
    decision = engine.evaluate(
        OrderIntent(symbol="PTT", side=Side.BUY, quantity=100, price=30.0),
        RiskContext(position_pct_after_trade=4.0),
    )
    assert decision.approved is False
    assert "stop loss is required for buy orders" in decision.reasons


def test_rejects_notional_over_available_line() -> None:
    engine = RiskEngine(Settings())
    decision = engine.evaluate(
        OrderIntent(symbol="CPALL", side=Side.BUY, quantity=1_000, price=60.0, stop_loss=57.0),
        RiskContext(position_pct_after_trade=5.0, line_available=50_000.0),
    )
    assert decision.approved is False
    assert "estimated notional exceeds available line" in decision.reasons


def test_portfolio_var_and_expected_shortfall() -> None:
    from zksato.risk import PortfolioRiskManager

    manager = PortfolioRiskManager(Settings())
    returns = [-0.05, -0.03, -0.02, 0.01, 0.02, 0.03, 0.04, 0.05, 0.01, -0.01]
    var_95 = manager.calculate_var(returns, confidence_level=0.95, portfolio_value=100_000.0)
    cvar_95 = manager.calculate_expected_shortfall(
        returns, confidence_level=0.95, portfolio_value=100_000.0
    )

    assert var_95 > 0.0
    assert cvar_95 >= var_95
