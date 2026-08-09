from zksato.domain import OrderRecord, OrderStatus, OrderType, Side
from zksato.store import StateStore


def _order(filled_quantity: int, average_fill_price: float) -> OrderRecord:
    return OrderRecord(
        broker_order_id="broker-1",
        client_order_id="client-1",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        filled_quantity=filled_quantity,
        order_type=OrderType.LIMIT,
        price=12.0,
        average_fill_price=average_fill_price,
        status=(OrderStatus.FILLED if filled_quantity == 100 else OrderStatus.PARTIALLY_FILLED),
    )


def test_cumulative_fill_snapshots_are_stored_as_incremental_deltas() -> None:
    store = StateStore()
    order = _order(40, 10.0)
    store.upsert_order(order)
    first = store.record_order_fill(order, source="reconciled")
    assert first is not None
    assert first.quantity == 40
    assert first.price == 10.0

    order.filled_quantity = 100
    order.average_fill_price = 11.0
    store.upsert_order(order)
    second = store.record_order_fill(order, source="reconciled")
    assert second is not None
    assert second.quantity == 60
    assert second.price == 700 / 60
    assert sum(fill.quantity for fill in store.list_fills()) == 100


def test_replaying_same_cumulative_snapshot_is_idempotent() -> None:
    store = StateStore()
    order = _order(100, 11.0)
    store.upsert_order(order)
    assert store.record_order_fill(order, source="submission") is not None
    assert store.record_order_fill(order, source="reconciled") is None
    assert store.filled_quantity_recorded(str(order.id)) == 100
