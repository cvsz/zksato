from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, Quote, Side
from zksato.service import TradingService
from zksato.store import StateStore


async def test_server_risk_context_uses_trusted_quote_and_portfolio() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=40, bid=39.75, offer=40.25))
    broker = PaperBroker(store, initial_cash=100_000)
    service = TradingService(Settings(), broker, store)
    context = await service.risk_context_for(
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40,
            stop_loss=38,
        )
    )
    assert context.market_data_available is True
    assert context.reference_price == 40
    assert context.line_available == 100_000
    assert context.opens_new_position is True
    assert context.spread_pct is not None


async def test_server_risk_context_fails_closed_without_market_data() -> None:
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000)
    service = TradingService(Settings(), broker, store)
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        price=40,
        stop_loss=38,
    )
    context = await service.risk_context_for(intent)
    decision = service.risk_engine.evaluate(intent, context)
    assert context.market_data_available is False
    assert decision.approved is False
    assert "trusted market data is unavailable" in decision.reasons
