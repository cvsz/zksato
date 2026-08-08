from __future__ import annotations

import asyncio
from contextlib import suppress

from zksato.broker.base import Broker
from zksato.domain import OrderRecord, OrderStatus, ReconciliationReport
from zksato.observability import RECONCILIATION_RUNS, RECONCILIATION_UNRESOLVED
from zksato.store import StateStore

OPEN_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.NEEDS_RECONCILIATION,
}


class ReconciliationService:
    def __init__(self, broker: Broker, store: StateStore) -> None:
        self.broker = broker
        self.store = store

    async def run(self) -> ReconciliationReport:
        remote_orders = await self.broker.list_orders()
        report = ReconciliationReport(examined_remote=len(remote_orders))
        remote_ids = {item.broker_order_id for item in remote_orders if item.broker_order_id}

        for remote in remote_orders:
            local = self._match(remote)
            if local is None:
                self.store.upsert_order(remote)
                report.inserted += 1
                continue
            merged = remote.model_copy(
                update={
                    "id": local.id,
                    "client_order_id": local.client_order_id or remote.client_order_id,
                    "stop_loss": local.stop_loss,
                    "take_profit": local.take_profit,
                    "source": local.source,
                    "created_at": local.created_at,
                }
            )
            if merged.model_dump() != local.model_dump():
                self.store.upsert_order(merged)
                report.updated += 1

        for local in self.store.list_orders():
            if local.status not in OPEN_STATUSES or not local.broker_order_id:
                continue
            if local.broker_order_id in remote_ids:
                continue
            local.status = OrderStatus.NEEDS_RECONCILIATION
            local.message = "open local order not present in broker order snapshot"
            self.store.upsert_order(local)
            report.marked_unknown += 1
            report.unresolved_order_ids.append(str(local.id))

        unresolved = [
            item
            for item in self.store.list_orders()
            if item.status == OrderStatus.NEEDS_RECONCILIATION
        ]
        RECONCILIATION_UNRESOLVED.set(len(unresolved))
        RECONCILIATION_RUNS.labels(result="success").inc()
        self.store.add_audit(
            "reconciliation.completed",
            "broker reconciliation completed",
            report.model_dump(mode="json"),
        )
        return report

    def _match(self, remote: OrderRecord) -> OrderRecord | None:
        if remote.broker_order_id:
            local = self.store.find_order_by_broker_order_id(remote.broker_order_id)
            if local is not None:
                return local
        if remote.client_order_id:
            return self.store.find_order_by_client_order_id(remote.client_order_id)
        return None


class ReconciliationWorker:
    def __init__(
        self,
        service: ReconciliationService,
        interval_seconds: float,
    ) -> None:
        self.service = service
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.service.run()
            except (RuntimeError, OSError, ValueError) as exc:
                RECONCILIATION_RUNS.labels(result="error").inc()
                self.service.store.add_audit("reconciliation.failed", str(exc))
            await asyncio.sleep(self.interval_seconds)
