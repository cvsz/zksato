from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def test_equity_short_is_rejected_by_default() -> None:
    decision = RiskEngine(Settings()).evaluate(
        OrderIntent(symbol="AOT", side=Side.SELL, quantity=100, price=40),
        RiskContext(reference_price=40, available_quantity=0, reduces_exposure=False),
    )
    assert decision.approved is False
    assert "equity short selling is disabled" in decision.reasons


def test_sell_above_holding_is_rejected() -> None:
    decision = RiskEngine(Settings()).evaluate(
        OrderIntent(symbol="AOT", side=Side.SELL, quantity=200, price=40),
        RiskContext(reference_price=40, available_quantity=100, reduces_exposure=False),
    )
    assert decision.approved is False
    assert "sell quantity exceeds available position" in decision.reasons
