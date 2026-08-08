from __future__ import annotations

import asyncio
from contextlib import suppress

from zksato.broker.base import Broker
from zksato.coordination import CoordinationBusyError, CoordinationManager
from zksato.domain import (
    FillRecord,
    OrderEvent,
    OrderRecord,
    OrderStatus,
    ReconciliationReport,
)
from zksato.observability import RECONCILIATION_RUNS, RECONCILIATION_UNRESOLVED
from zksato.store import StateStore

OPEN_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.NEEDS_RECONCILIATION,
}


class ReconciliationService:
    def __init__(
        self,
        broker: Broker,
        store: StateStore,
        coordination: CoordinationManager | None = None,
    ) -> None:
        self.broker = broker
        self.store = store
        self.coordination = coordination

    async def run(self) -> ReconciliationReport:
        if self.coordination is None:
            return await self._run_locked()
        try:
            async with self.coordination.lock("broker-reconciliation"):
                return await self._run_locked()
        except CoordinationBusyError:
            return ReconciliationReport()

    async def _run_locked(self) -> ReconciliationReport:
        remote_orders = await self.broker.list_orders()
        report = ReconciliationReport(examined_remote=len(remote_orders))
        remote_ids = {item.broker_order_id for item in remote_orders if item.broker_order_id}

        for remote in remote_orders:
            local = self._match(remote)
            if local is None:
                self.store.upsert_order(remote)
                self.store.add_order_event(
                    OrderEvent(
                        order_id=remote.id,
                        event_type="reconciliation_inserted",
                        status=remote.status,
                        data={"broker_order_id": remote.broker_order_id or ""},
                    )
                )
                report.inserted += 1
                self._record_fill(remote, report)
                continue
            merged = remote.model_copy(
                update={
                    "id": local.id,
                    "client_order_id": local.client_order_id or remote.client_order_id,
                    "stop_loss": local.stop_loss,
                    "take_profit": local.take_profit,
                    "source": local.source,
                    "created_at": local.created_at,
                    "correlation_id": local.correlation_id or remote.correlation_id,
                }
            )
            if merged.model_dump() != local.model_dump():
                self.store.upsert_order(merged)
                self.store.add_order_event(
                    OrderEvent(
                        order_id=merged.id,
                        event_type="reconciliation_updated",
                        status=merged.status,
                        data={
                            "broker_order_id": merged.broker_order_id or "",
                            "filled_quantity": merged.filled_quantity,
                        },
                    )
                )
                report.updated += 1
            self._record_fill(merged, report)

        for local in self.store.list_orders():
            if local.status not in OPEN_STATUSES or not local.broker_order_id:
                continue
            if local.broker_order_id in remote_ids:
                continue
            local.status = OrderStatus.NEEDS_RECONCILIATION
            local.message = "open local order not present in broker order snapshot"
            self.store.upsert_order(local)
            self.store.add_order_event(
                OrderEvent(
                    order_id=local.id,
                    event_type="reconciliation_missing_remote",
                    status=local.status,
                    data={"broker_order_id": local.broker_order_id},
                )
            )
            report.marked_unknown += 1
            report.unresolved_order_ids.append(str(local.id))

        unresolved = [
            item
            for item in self.store.list_orders()
            if item.status == OrderStatus.NEEDS_RECONCILIATION
        ]
        ready = not unresolved
        RECONCILIATION_UNRESOLVED.set(len(unresolved))
        RECONCILIATION_RUNS.labels(result="success" if ready else "unresolved").inc()
        self.store.set_broker_reconciliation_ready(ready)
        self.store.add_audit(
            "reconciliation.completed",
            "broker reconciliation completed",
            {**report.model_dump(mode="json"), "ready": ready},
        )
        return report

    def _record_fill(self, order: OrderRecord, report: ReconciliationReport) -> None:
        if order.filled_quantity <= 0 or not order.average_fill_price:
            return
        before = len(self.store.list_fills(limit=10_000))
        self.store.add_fill(
            FillRecord(
                broker_fill_id=(
                    f"{order.broker_order_id}:{order.filled_quantity}"
                    if order.broker_order_id
                    else f"reconciled:{order.id}:{order.filled_quantity}"
                ),
                order_id=order.id,
                broker_order_id=order.broker_order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.filled_quantity,
                price=order.average_fill_price,
            )
        )
        after = len(self.store.list_fills(limit=10_000))
        if after > before:
            report.fills_recorded += 1

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
            self.service.store.set_broker_reconciliation_ready(False)
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self.service.store.set_broker_reconciliation_ready(False)

    async def _run(self) -> None:
        while True:
            try:
                await self.service.run()
            except (RuntimeError, OSError, ValueError) as exc:
                self.service.store.set_broker_reconciliation_ready(False)
                RECONCILIATION_RUNS.labels(result="error").inc()
                self.service.store.add_audit("reconciliation.failed", str(exc))
            await asyncio.sleep(self.interval_seconds)
