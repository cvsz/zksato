"""Tests for reconciliation module."""

from __future__ import annotations

import asyncio

import pytest

from zksato.broker.base import Broker
from zksato.coordination import CoordinationManager
from zksato.domain import OrderRecord, OrderStatus, ReconciliationReport, Side
from zksato.reconcile import ReconciliationService, ReconciliationWorker
from zksato.store import StateStore


class MockBroker(Broker):
    def __init__(self, orders: list[OrderRecord] | None = None):
        self._orders = orders or []
        self.cancelled: list[str] = []

    async def place_order(self, intent) -> OrderRecord:
        raise NotImplementedError("Use list_orders for reconciliation tests")

    async def cancel_order(self, order_id: str) -> OrderRecord:
        self.cancelled.append(order_id)
        return OrderRecord(
            symbol="TEST",
            side=Side.BUY,
            quantity=100,
            order_type="limit",
            price=100.0,
            status=OrderStatus.CANCELLED,
        )

    async def list_orders(self) -> list[OrderRecord]:
        return self._orders

    async def portfolio(self):
        raise NotImplementedError


def _make_order(
    symbol: str = "AAPL",
    side: Side = Side.BUY,
    quantity: float = 100.0,
    status: OrderStatus = OrderStatus.ACCEPTED,
    broker_order_id: str | None = None,
    client_order_id: str | None = None,
    filled_quantity: float = 0.0,
    source: str = "test",
    average_fill_price: float | None = None,
) -> OrderRecord:
    return OrderRecord(
        symbol=symbol,
        side=side,
        quantity=quantity,
        filled_quantity=filled_quantity,
        order_type="limit",
        price=100.0,
        status=status,
        broker_order_id=broker_order_id,
        client_order_id=client_order_id,
        source=source,
        average_fill_price=average_fill_price,
    )


class TestReconciliationService:
    @pytest.fixture
    def mock_broker(self) -> MockBroker:
        return MockBroker()

    @pytest.fixture
    def store(self) -> StateStore:
        from zksato.store import StateStore

        return StateStore()

    @pytest.fixture
    def service(self, mock_broker: MockBroker, store: StateStore) -> ReconciliationService:
        return ReconciliationService(broker=mock_broker, store=store)

    def test_reconciliation_inserts_new_remote_orders(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        remote = _make_order(broker_order_id="broker_123", symbol="AAPL")
        mock_broker._orders = [remote]

        report = service.run()
        import asyncio

        report = asyncio.run(report)

        assert report.examined_remote == 1
        assert report.inserted == 1
        assert len(store.list_orders()) == 1
        inserted = store.list_orders()[0]
        assert inserted.broker_order_id == "broker_123"

    def test_reconciliation_updates_existing_order(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.ACCEPTED,
            filled_quantity=0.0,
        )
        store.upsert_order(local)

        remote = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.FILLED,
            filled_quantity=100.0,
        )
        mock_broker._orders = [remote]

        report = asyncio.run(service.run())

        assert report.examined_remote == 1
        assert report.updated == 1
        assert report.inserted == 0
        updated = store.list_orders()[0]
        assert updated.status == OrderStatus.FILLED
        assert updated.filled_quantity == 100.0

    def test_reconciliation_preserves_local_identity_fields(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            client_order_id="client_456",
            status=OrderStatus.ACCEPTED,
            source="test_source",
            side=Side.BUY,
            quantity=100.0,
        )
        store.upsert_order(local)

        remote = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.FILLED,
            filled_quantity=100.0,
            side=Side.SELL,  # Different from local - should trigger divergence
        )
        mock_broker._orders = [remote]

        report = asyncio.run(service.run())

        assert report.divergence_count == 1
        assert len(report.divergences) == 1
        div = report.divergences[0]
        assert "side" in div["fields"]
        # Local identity preserved
        updated = store.list_orders()[0]
        assert updated.client_order_id == "client_456"
        assert updated.source == "test_source"

    def test_reconciliation_marks_missing_remote_as_unknown(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.ACCEPTED,
        )
        store.upsert_order(local)
        mock_broker._orders = []  # Broker doesn't know about this order

        report = asyncio.run(service.run())

        assert report.marked_unknown == 1
        assert len(report.unresolved_order_ids) == 1
        updated = store.list_orders()[0]
        assert updated.status == OrderStatus.NEEDS_RECONCILIATION

    def test_reconciliation_records_fills(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.ACCEPTED,
            filled_quantity=0.0,
        )
        store.upsert_order(local)

        remote = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.FILLED,
            filled_quantity=100.0,
            average_fill_price=100.0,
        )
        mock_broker._orders = [remote]

        report = asyncio.run(service.run())

        assert report.fills_recorded == 1
        fills = store.list_fills()
        assert len(fills) == 1
        assert fills[0].quantity == 100.0

    def test_reconciliation_ready_when_no_unresolved(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.FILLED,
        )
        store.upsert_order(local)
        mock_broker._orders = [local]

        report = asyncio.run(service.run())

        assert report.unresolved_order_ids == []
        assert store.broker_reconciliation_ready() is True

    def test_reconciliation_not_ready_when_unresolved(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        local = _make_order(
            broker_order_id="broker_123",
            symbol="AAPL",
            status=OrderStatus.ACCEPTED,
        )
        store.upsert_order(local)
        mock_broker._orders = []

        report = asyncio.run(service.run())

        assert len(report.unresolved_order_ids) == 1
        assert store.broker_reconciliation_ready() is False

    def test_reconciliation_with_coordination_lock(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        coordination = CoordinationManager(redis_url=None)
        service.coordination = coordination

        remote = _make_order(broker_order_id="broker_123", symbol="AAPL")
        mock_broker._orders = [remote]

        report = asyncio.run(service.run())
        assert report.examined_remote == 1
        assert report.inserted == 1

    def test_reconciliation_coordination_busy_returns_empty_report(
        self,
        service: ReconciliationService,
        mock_broker: MockBroker,
        store: StateStore,
    ) -> None:
        coordination = CoordinationManager(redis_url=None)
        service.coordination = coordination

        # Acquire the lock first and hold it in the same event loop
        async def test_busy():
            lock_ctx = coordination.lock("broker-reconciliation")
            await lock_ctx.__aenter__()

            # Now try to run reconciliation - should return empty report due to busy
            remote = _make_order(broker_order_id="broker_123", symbol="AAPL")
            mock_broker._orders = [remote]

            report = await service.run()
            assert isinstance(report, ReconciliationReport)
            assert report.examined_remote == 0

            # Release the lock
            await lock_ctx.__aexit__(None, None, None)

        asyncio.run(test_busy())


class TestReconciliationWorker:
    @pytest.fixture
    def mock_broker(self) -> MockBroker:
        return MockBroker()

    @pytest.fixture
    def store(self) -> StateStore:
        return StateStore()

    @pytest.fixture
    def service(self, mock_broker: MockBroker, store: StateStore) -> ReconciliationService:
        return ReconciliationService(broker=mock_broker, store=store)

    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self, service: ReconciliationService) -> None:
        worker = ReconciliationWorker(service=service, interval_seconds=0.1)
        worker.start()
        assert worker._task is not None
        assert not worker._task.done()

        await worker.stop()
        assert worker._task is None
        assert service.store.broker_reconciliation_ready() is False

    @pytest.mark.asyncio
    async def test_worker_runs_reconciliation(
        self, service: ReconciliationService, mock_broker: MockBroker
    ) -> None:
        remote = _make_order(broker_order_id="broker_123", symbol="AAPL")
        mock_broker._orders = [remote]

        worker = ReconciliationWorker(service=service, interval_seconds=0.01)
        worker.start()

        # Wait for at least one reconciliation cycle
        await asyncio.sleep(0.1)
        # Check readiness BEFORE stopping the worker
        assert service.store.broker_reconciliation_ready() is True
        await worker.stop()


# Need to import StateStore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
