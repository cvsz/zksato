from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def test_rejects_stale_quote_and_excess_open_orders() -> None:
    engine = RiskEngine(Settings(market_data_stale_seconds=5, max_open_orders=2))
    decision = engine.evaluate(
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
        ),
        RiskContext(
            open_orders=2,
            quote_age_seconds=6,
            position_pct_after_trade=5,
            portfolio_value=500_000,
        ),
    )
    assert decision.approved is False
    assert "maximum open order count reached" in decision.reasons
    assert "market quote is stale" in decision.reasons
