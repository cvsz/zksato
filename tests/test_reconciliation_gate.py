import pytest

from zksato.broker.base import BrokerAmbiguousError
from zksato.config import Settings
from zksato.domain import (
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderSubmission,
    OrderType,
    PortfolioSnapshot,
    RiskContext,
    Side,
)
from zksato.reconcile import ReconciliationService
from zksato.service import TradingModeError, TradingService
from zksato.store import StateStore


class FakeBroker:
    def __init__(self) -> None:
        self.cancel_arg: str | None = None
        self.cancel_ambiguous = False
        self.orders: list[OrderRecord] = []

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        return OrderRecord(
            broker_order_id="B-1",
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            order_type=intent.order_type,
            price=intent.price,
            status=OrderStatus.ACCEPTED,
        )

    async def cancel_order(self, order_id: str) -> OrderRecord:
        self.cancel_arg = order_id
        if self.cancel_ambiguous:
            raise BrokerAmbiguousError("timeout after cancel")
        source = self.orders[0]
        return source.model_copy(update={"status": OrderStatus.CANCELLED})

    async def list_orders(self) -> list[OrderRecord]:
        return self.orders

    async def portfolio(self) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            cash=500_000,
            market_value=0,
            equity=500_000,
            realized_pnl=0,
            unrealized_pnl=0,
            daily_pnl=0,
        )


def configured_settings() -> Settings:
    return Settings(
        trading_mode="sandbox",
        reconciliation_enabled=True,
        settrade_app_id="id",
        settrade_app_secret="secret",
        settrade_broker_id="broker",
        settrade_account_no="acct",
        settrade_pin="123456",
    )


async def test_nonpaper_execution_waits_for_first_reconciliation() -> None:
    store = StateStore()
    broker = FakeBroker()
    service = TradingService(configured_settings(), broker, store)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40,
            stop_loss=38,
        ),
        risk=RiskContext(
            position_pct_after_trade=5,
            line_available=500_000,
            portfolio_value=500_000,
        ),
    )
    with pytest.raises(TradingModeError, match="reconciliation"):
        await service.submit(submission)

    await ReconciliationService(broker, store).run()
    order = await service.submit(submission)
    assert order.broker_order_id == "B-1"


async def test_cancel_uses_broker_order_id_and_preserves_local_id() -> None:
    store = StateStore()
    broker = FakeBroker()
    service = TradingService(configured_settings(), broker, store)
    local = OrderRecord(
        broker_order_id="B-9",
        client_order_id="client-9",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=40,
        status=OrderStatus.ACCEPTED,
        source="manual",
    )
    store.upsert_order(local)
    broker.orders = [local.model_copy(update={"id": local.id})]
    cancelled = await service.cancel_order(str(local.id))
    assert broker.cancel_arg == "B-9"
    assert cancelled.id == local.id
    assert cancelled.client_order_id == "client-9"
    assert cancelled.status == OrderStatus.CANCELLED


async def test_ambiguous_cancel_marks_reconciliation_required() -> None:
    store = StateStore()
    broker = FakeBroker()
    service = TradingService(configured_settings(), broker, store)
    local = OrderRecord(
        broker_order_id="B-10",
        symbol="PTT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=30,
        status=OrderStatus.ACCEPTED,
    )
    store.upsert_order(local)
    store.set_broker_reconciliation_ready(True)
    broker.orders = [local]
    broker.cancel_ambiguous = True
    result = await service.cancel_order(str(local.id))
    assert result.status == OrderStatus.NEEDS_RECONCILIATION
    assert store.broker_reconciliation_ready() is False


async def test_list_orders_is_local_reconciled_view() -> None:
    store = StateStore()
    broker = FakeBroker()
    service = TradingService(configured_settings(), broker, store)
    local = OrderRecord(
        broker_order_id="B-20",
        symbol="KBANK",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=130,
        status=OrderStatus.ACCEPTED,
    )
    store.upsert_order(local)
    broker.orders = []
    rows = await service.list_orders()
    assert len(rows) == 1
    assert rows[0].id == local.id
