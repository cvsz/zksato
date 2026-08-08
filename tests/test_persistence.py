from zksato.domain import OrderRecord, OrderStatus, OrderType, Side
from zksato.persistence import SqlStateStore


def test_sql_store_persists_orders_and_idempotency(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'state.db'}"
    store = SqlStateStore(database_url)
    assert store.claim_client_order_id("client-1") is True
    order = OrderRecord(
        client_order_id="client-1",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=40.0,
        status=OrderStatus.ACCEPTED,
    )
    store.upsert_order(order)
    store.close()

    recovered = SqlStateStore(database_url)
    assert recovered.claim_client_order_id("client-1") is False
    loaded = recovered.find_order_by_client_order_id("client-1")
    assert loaded is not None
    assert loaded.symbol == "AOT"
    recovered.close()
