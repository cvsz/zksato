from datetime import UTC, datetime

from zksato.domain import (
    Bar,
    FillRecord,
    OrderEvent,
    OrderRecord,
    OrderStatus,
    OrderType,
    RiskEvaluation,
    Side,
)
from zksato.persistence import SqlStateStore


def test_priority_state_survives_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'state.db'}"
    store = SqlStateStore(database_url)
    order = OrderRecord(
        broker_order_id="B-1",
        client_order_id="C-1",
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        filled_quantity=100,
        order_type=OrderType.LIMIT,
        price=40,
        average_fill_price=40,
        status=OrderStatus.FILLED,
    )
    store.upsert_order(order)
    store.add_order_event(
        OrderEvent(order_id=order.id, event_type="filled", status=OrderStatus.FILLED)
    )
    store.add_fill(
        FillRecord(
            broker_fill_id="F-1",
            order_id=order.id,
            broker_order_id="B-1",
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40,
        )
    )
    store.add_risk_evaluation(
        RiskEvaluation(
            client_order_id="C-1",
            symbol="AOT",
            approved=True,
            actor="test",
        )
    )
    store.upsert_bar(
        Bar(
            symbol="AOT",
            timestamp=datetime(2026, 8, 9, tzinfo=UTC),
            open=40,
            high=41,
            low=39,
            close=40.5,
            volume=1000,
            source="test",
        )
    )
    store.set_broker_reconciliation_ready(True)
    store.close()

    recovered = SqlStateStore(database_url)
    assert len(recovered.list_orders()) == 1
    assert len(recovered.list_order_events()) == 1
    assert len(recovered.list_fills()) == 1
    assert len(recovered.list_risk_evaluations()) == 1
    assert len(recovered.list_bars("AOT")) == 1
    assert recovered.broker_reconciliation_ready() is True
    recovered.close()
