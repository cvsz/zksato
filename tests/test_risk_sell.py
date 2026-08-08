from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def test_sell_can_reduce_oversized_position_after_daily_loss() -> None:
    decision = RiskEngine(Settings(max_position_pct=10, max_daily_loss_pct=2)).evaluate(
        OrderIntent(symbol="AOT", side=Side.SELL, quantity=100, price=40),
        RiskContext(
            position_pct_after_trade=50,
            reference_price=40,
            daily_pnl_pct=-5,
            reduces_exposure=True,
        ),
    )
    assert decision.approved is True
