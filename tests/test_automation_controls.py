import pytest

from zksato.automation import AutomationEngine
from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import BotConfig, BotState, OrderIntent, Quote, Side, StrategyConfig
from zksato.service import TradingService
from zksato.store import StateStore


def _engine() -> tuple[AutomationEngine, StateStore, PaperBroker]:
    settings = Settings(trading_mode="paper", auth_required=False)
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000, match_resting_limits=True)
    service = TradingService(settings=settings, broker=broker, store=store)
    return AutomationEngine(settings=settings, store=store, service=service), store, broker


def test_bot_pause_resume_preserves_configuration() -> None:
    engine, _, _ = _engine()
    config = BotConfig(symbols=["AOT"], strategy=StrategyConfig(name="ema_cross"))
    assert engine.start(config).state == BotState.RUNNING
    assert engine.pause().state == BotState.PAUSED
    assert engine.status.config is config
    assert engine.resume().state == BotState.RUNNING
    assert engine.stop().state == BotState.STOPPED


def test_resume_without_configuration_fails_closed() -> None:
    engine, _, _ = _engine()
    engine.status.state = BotState.PAUSED
    with pytest.raises(ValueError, match="no configuration"):
        engine.resume()


@pytest.mark.asyncio
async def test_quote_ingestion_matches_resting_paper_limits() -> None:
    engine, store, broker = _engine()
    store.update_quote(Quote(symbol="AOT", last=40.0, bid=39.5, offer=40.5))
    order = await broker.place_order(
        OrderIntent(symbol="AOT", side=Side.BUY, quantity=10, price=39.0)
    )
    assert order.filled_quantity == 0
    await engine.on_quote(Quote(symbol="AOT", last=38.8, bid=38.7, offer=38.9))
    stored = store.find_order(str(order.id))
    assert stored is not None
    assert stored.filled_quantity == 10
