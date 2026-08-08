from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def test_sell_can_reduce_oversized_position() -> None:
    decision = RiskEngine(Settings(max_position_pct=10)).evaluate(
        OrderIntent(symbol="AOT", side=Side.SELL, quantity=100, price=40),
        RiskContext(position_pct_after_trade=50, reference_price=40),
    )
    assert decision.approved is True
