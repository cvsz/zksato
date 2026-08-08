import pytest

from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderSubmission, RiskContext, Side
from zksato.service import RiskRejectedError, TradingModeError, TradingService
from zksato.store import StateStore


def make_service(settings: Settings | None = None) -> TradingService:
    configured = settings or Settings(trading_mode="paper")
    store = StateStore()
    broker = PaperBroker(store=store, initial_cash=500_000)
    return TradingService(configured, broker, store)


@pytest.mark.asyncio
async def test_paper_order_is_filled() -> None:
    service = make_service()
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="test-1",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    order = await service.submit(submission)
    assert order.symbol == "AOT"
    assert order.client_order_id == "test-1"
    assert order.filled_quantity == 100


@pytest.mark.asyncio
async def test_duplicate_client_order_id_is_rejected() -> None:
    service = make_service()
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="same-id",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    await service.submit(submission)
    with pytest.raises(ValueError, match="duplicate client_order_id"):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_risk_rejection_prevents_execution() -> None:
    service = make_service()
    submission = OrderSubmission(
        intent=OrderIntent(symbol="AOT", side=Side.BUY, quantity=100, price=40.0),
        risk=RiskContext(position_pct_after_trade=5.0),
    )
    with pytest.raises(RiskRejectedError):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_non_paper_mode_requires_settrade_configuration() -> None:
    service = make_service(Settings(trading_mode="sandbox", live_trading_enabled=False))
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT", side=Side.BUY, quantity=100, price=40.0, stop_loss=38.0
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    with pytest.raises(TradingModeError, match="credentials"):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_live_automation_is_never_allowed() -> None:
    settings = Settings(
        trading_mode="live",
        live_trading_enabled=True,
        live_confirmation_token="secret",
        settrade_app_id="id",
        settrade_app_secret="secret",
        settrade_broker_id="broker",
        settrade_account_no="acct",
        settrade_pin="123456",
    )
    service = make_service(settings)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
        confirmation_token="secret",
    )
    with pytest.raises(TradingModeError, match="autonomous live"):
        await service.submit(submission, automated=True)
