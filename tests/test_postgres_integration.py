import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from zksato.domain import OrderRecord, OrderStatus, OrderType, Side
from zksato.persistence import SqlStateStore

load_dotenv()


def test_postgres_round_trip_and_idempotency() -> None:
    database_url = os.getenv("ZKSATO_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL integration URL is not configured")
    client_order_id = f"ci-{uuid4()}"
    store = SqlStateStore(database_url)
    assert store.claim_client_order_id(client_order_id) is True
    order = OrderRecord(
        client_order_id=client_order_id,
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=40,
        status=OrderStatus.ACCEPTED,
    )
    store.upsert_order(order)
    store.close()

    recovered = SqlStateStore(database_url)
    assert recovered.claim_client_order_id(client_order_id) is False
    loaded = recovered.find_order_by_client_order_id(client_order_id)
    assert loaded is not None
    assert loaded.id == order.id
    recovered.close()
