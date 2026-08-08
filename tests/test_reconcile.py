from zksato.domain import OrderRecord, OrderStatus, OrderType, Side
from zksato.reconcile import ReconciliationService
from zksato.store import StateStore


class FakeBroker:
    def __init__(self, orders: list[OrderRecord]) -> None:
        self.orders = orders

    async def list_orders(self) -> list[OrderRecord]:
        return self.orders


async def test_reconciliation_updates_local_order() -> None:
    store = StateStore()
    local = OrderRecord(
        broker_order_id="123",
        client_order_id="client-1",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=40.0,
        status=OrderStatus.ACCEPTED,
    )
    store.upsert_order(local)
    remote = OrderRecord(
        broker_order_id="123",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        filled_quantity=100,
        order_type=OrderType.LIMIT,
        price=40.0,
        status=OrderStatus.FILLED,
    )
    report = await ReconciliationService(FakeBroker([remote]), store).run()  # type: ignore[arg-type]
    assert report.updated == 1
    assert store.find_order_by_broker_order_id("123").status == OrderStatus.FILLED
