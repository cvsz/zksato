import pytest

from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderSubmission, RiskContext, Side
from zksato.service import RiskRejectedError, TradingModeError, TradingService


@pytest.mark.asyncio
async def test_paper_order_is_accepted() -> None:
    service = TradingService(Settings(trading_mode="paper"), PaperBroker())
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="test-1",
        ),
        risk=RiskContext(position_pct_after_trade=5.0, line_available=100_000.0),
    )
    order = await service.submit(submission)
    assert order.symbol == "AOT"
    assert order.client_order_id == "test-1"


@pytest.mark.asyncio
async def test_duplicate_client_order_id_is_rejected() -> None:
    service = TradingService(Settings(trading_mode="paper"), PaperBroker())
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="same-id",
        ),
        risk=RiskContext(position_pct_after_trade=5.0, line_available=100_000.0),
    )
    await service.submit(submission)
    with pytest.raises(ValueError, match="duplicate client_order_id"):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_risk_rejection_prevents_execution() -> None:
    service = TradingService(Settings(trading_mode="paper"), PaperBroker())
    submission = OrderSubmission(
        intent=OrderIntent(symbol="AOT", side=Side.BUY, quantity=100, price=40.0),
        risk=RiskContext(position_pct_after_trade=5.0),
    )
    with pytest.raises(RiskRejectedError):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_non_paper_mode_never_silently_uses_paper_broker() -> None:
    service = TradingService(
        Settings(trading_mode="sandbox", live_trading_enabled=False),
        PaperBroker(),
    )
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT", side=Side.BUY, quantity=100, price=40.0, stop_loss=38.0
        ),
        risk=RiskContext(position_pct_after_trade=5.0, line_available=100_000.0),
    )
    with pytest.raises(TradingModeError):
        await service.submit(submission)
