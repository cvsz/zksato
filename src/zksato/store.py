from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock

from zksato.domain import (
    AccountSnapshot,
    AlertRule,
    AuditEvent,
    Bar,
    FillRecord,
    OrderEvent,
    OrderRecord,
    OutboxMessage,
    Quote,
    RiskEvaluation,
    Signal,
    StrategyRun,
    StrategyVersion,
)
from zksato.outbox_delivery import OutboxDeliveryState, ensure_utc


class StateStore:
    """Thread-safe state adapter used by the paper runtime and as a persistence contract."""

    def __init__(self, history_size: int = 1000) -> None:
        self._lock = RLock()
        self.quotes: dict[str, Quote] = {}
        self.price_history: dict[str, deque[float]] = {}
        self.orders: list[OrderRecord] = []
        self.order_events: deque[OrderEvent] = deque(maxlen=history_size * 4)
        self.fills: deque[FillRecord] = deque(maxlen=history_size * 4)
        self.risk_evaluations: deque[RiskEvaluation] = deque(maxlen=history_size * 4)
        self.account_snapshots: deque[AccountSnapshot] = deque(maxlen=history_size)
        self.strategy_versions: dict[str, StrategyVersion] = {}
        self.strategy_runs: deque[StrategyRun] = deque(maxlen=history_size * 2)
        self.bars: dict[str, Bar] = {}
        self.signals: deque[Signal] = deque(maxlen=history_size)
        self.audit: deque[AuditEvent] = deque(maxlen=history_size)
        self.alerts: dict[str, AlertRule] = {}
        self.outbox: dict[str, OutboxMessage] = {}
        self.outbox_delivery: dict[str, OutboxDeliveryState] = {}
        self.paper_account: dict[str, object] | None = None
        self._client_order_ids: set[str] = set()
        self._history_size = history_size
        self._broker_reconciliation_ready = False

    def update_quote(self, quote: Quote) -> Quote:
        with self._lock:
            current = self.quotes.get(quote.symbol)
            if current is not None and quote.timestamp < current.timestamp:
                return current
            self.quotes[quote.symbol] = quote
            history = self.price_history.setdefault(quote.symbol, deque(maxlen=self._history_size))
            history.append(quote.last)
            return quote

    def get_quote(self, symbol: str) -> Quote | None:
        with self._lock:
            return self.quotes.get(symbol.upper())

    def list_quotes(self) -> list[Quote]:
        with self._lock:
            return sorted(self.quotes.values(), key=lambda item: item.symbol)

    def get_prices(self, symbol: str) -> list[float]:
        with self._lock:
            return list(self.price_history.get(symbol.upper(), ()))

    def quote_age_seconds(self, symbol: str) -> float | None:
        quote = self.get_quote(symbol)
        if quote is None:
            return None
        timestamp = quote.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return max(0.0, (datetime.now(UTC) - timestamp).total_seconds())

    def add_order(self, order: OrderRecord) -> OrderRecord:
        return self.upsert_order(order)

    def upsert_order(self, order: OrderRecord) -> OrderRecord:
        with self._lock:
            for index, existing in enumerate(self.orders):
                if existing.id == order.id:
                    self.orders[index] = order
                    return order
            self.orders.append(order)
            return order

    def list_orders(self) -> list[OrderRecord]:
        with self._lock:
            return list(reversed(self.orders))

    def find_order(self, order_id: str) -> OrderRecord | None:
        with self._lock:
            return next(
                (
                    order
                    for order in self.orders
                    if str(order.id) == order_id or order.broker_order_id == order_id
                ),
                None,
            )

    def find_order_by_client_order_id(self, client_order_id: str) -> OrderRecord | None:
        with self._lock:
            return next(
                (order for order in self.orders if order.client_order_id == client_order_id),
                None,
            )

    def find_order_by_broker_order_id(self, broker_order_id: str) -> OrderRecord | None:
        with self._lock:
            return next(
                (order for order in self.orders if order.broker_order_id == broker_order_id),
                None,
            )

    def add_order_event(self, event: OrderEvent) -> OrderEvent:
        with self._lock:
            self.order_events.append(event)
        return event

    def list_order_events(self, limit: int = 200) -> list[OrderEvent]:
        with self._lock:
            return list(reversed(self.order_events))[:limit]

    def add_fill(self, fill: FillRecord) -> FillRecord:
        with self._lock:
            if fill.broker_fill_id:
                existing = next(
                    (item for item in self.fills if item.broker_fill_id == fill.broker_fill_id),
                    None,
                )
                if existing is not None:
                    return existing
            self.fills.append(fill)
        return fill

    def list_fills(self, limit: int = 200) -> list[FillRecord]:
        with self._lock:
            return list(reversed(self.fills))[:limit]

    def filled_quantity_recorded(self, order_id: str) -> int:
        with self._lock:
            return sum(
                item.quantity
                for item in self.fills
                if item.order_id is not None and str(item.order_id) == order_id
            )

    def record_order_fill(self, order: OrderRecord, *, source: str) -> FillRecord | None:
        """Persist only the newly-filled delta for a cumulative broker/order snapshot."""

        if order.filled_quantity <= 0 or not order.average_fill_price:
            return None
        with self._lock:
            prior = [
                item
                for item in self.fills
                if item.order_id is not None and item.order_id == order.id
            ]
            recorded_quantity = sum(item.quantity for item in prior)
            delta_quantity = order.filled_quantity - recorded_quantity
            if delta_quantity <= 0:
                return None
            cumulative_value = order.average_fill_price * order.filled_quantity
            prior_value = sum(item.price * item.quantity for item in prior)
            delta_value = cumulative_value - prior_value
            delta_price = (
                delta_value / delta_quantity if delta_value > 0 else order.average_fill_price
            )
            fill = FillRecord(
                broker_fill_id=(
                    f"{source}:{order.broker_order_id or order.id}:{order.filled_quantity}"
                ),
                order_id=order.id,
                broker_order_id=order.broker_order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=delta_quantity,
                price=delta_price,
            )
        return self.add_fill(fill)

    def add_risk_evaluation(self, evaluation: RiskEvaluation) -> RiskEvaluation:
        with self._lock:
            self.risk_evaluations.append(evaluation)
        return evaluation

    def list_risk_evaluations(self, limit: int = 200) -> list[RiskEvaluation]:
        with self._lock:
            return list(reversed(self.risk_evaluations))[:limit]

    def add_account_snapshot(self, snapshot: AccountSnapshot) -> AccountSnapshot:
        with self._lock:
            self.account_snapshots.append(snapshot)
        return snapshot

    def list_account_snapshots(self, limit: int = 200) -> list[AccountSnapshot]:
        with self._lock:
            return list(reversed(self.account_snapshots))[:limit]

    def add_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        key = f"{version.name}:{version.version}"
        with self._lock:
            existing = self.strategy_versions.get(key)
            if existing is not None:
                if existing.code_hash == version.code_hash and existing.config == version.config:
                    return existing
                raise ValueError(f"strategy version {key} is immutable")
            self.strategy_versions[key] = version
        return version

    def list_strategy_versions(self) -> list[StrategyVersion]:
        with self._lock:
            return sorted(
                self.strategy_versions.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )

    def add_strategy_run(self, run: StrategyRun) -> StrategyRun:
        with self._lock:
            self.strategy_runs.append(run)
        return run

    def list_strategy_runs(self, limit: int = 200) -> list[StrategyRun]:
        with self._lock:
            return list(reversed(self.strategy_runs))[:limit]

    @staticmethod
    def _bar_key(bar: Bar) -> str:
        return f"{bar.symbol}:{bar.timeframe}:{bar.timestamp.isoformat()}"

    def upsert_bar(self, bar: Bar) -> Bar:
        with self._lock:
            self.bars[self._bar_key(bar)] = bar
        return bar

    def list_bars(self, symbol: str, timeframe: str = "1m", limit: int = 5000) -> list[Bar]:
        normalized = symbol.upper()
        with self._lock:
            rows = [
                item
                for item in self.bars.values()
                if item.symbol == normalized and item.timeframe == timeframe
            ]
        rows.sort(key=lambda item: item.timestamp)
        return rows[-limit:]

    def claim_client_order_id(self, client_order_id: str) -> bool:
        with self._lock:
            if client_order_id in self._client_order_ids:
                return False
            self._client_order_ids.add(client_order_id)
            return True

    def release_client_order_id(self, client_order_id: str) -> None:
        with self._lock:
            self._client_order_ids.discard(client_order_id)

    def set_broker_reconciliation_ready(self, ready: bool) -> None:
        with self._lock:
            self._broker_reconciliation_ready = ready

    def broker_reconciliation_ready(self) -> bool:
        with self._lock:
            return self._broker_reconciliation_ready

    def save_paper_account(self, payload: dict[str, object]) -> None:
        with self._lock:
            self.paper_account = dict(payload)

    def get_paper_account(self) -> dict[str, object] | None:
        with self._lock:
            return dict(self.paper_account) if self.paper_account is not None else None

    def add_signal(self, signal: Signal) -> Signal:
        with self._lock:
            self.signals.append(signal)
            return signal

    def list_signals(self, limit: int = 100) -> list[Signal]:
        with self._lock:
            return list(reversed(self.signals))[:limit]

    def add_alert(self, alert: AlertRule) -> AlertRule:
        with self._lock:
            self.alerts[str(alert.id)] = alert
            return alert

    def delete_alert(self, alert_id: str) -> bool:
        with self._lock:
            return self.alerts.pop(alert_id, None) is not None

    def list_alerts(self) -> list[AlertRule]:
        with self._lock:
            return list(self.alerts.values())

    def add_audit(
        self,
        event_type: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> AuditEvent:
        payload = data or {}
        with self._lock:
            previous_hash = self.audit[-1].event_hash if self.audit else None
            correlation_id = payload.get("correlation_id")
            event = AuditEvent(
                event_type=event_type,
                message=message,
                data=payload,
                previous_hash=previous_hash,
                correlation_id=str(correlation_id) if correlation_id else None,
                timestamp=datetime.now(UTC),
            )
            canonical = json.dumps(
                event.model_dump(mode="json", exclude={"event_hash"}),
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            event.event_hash = hashlib.sha256(canonical.encode()).hexdigest()
            self.audit.append(event)
        return event

    def list_audit(self, limit: int = 100) -> list[AuditEvent]:
        with self._lock:
            return list(reversed(self.audit))[:limit]

    def verify_audit_chain(self) -> bool:
        with self._lock:
            previous_hash: str | None = None
            for event in self.audit:
                if event.previous_hash != previous_hash or not event.event_hash:
                    return False
                canonical = json.dumps(
                    event.model_dump(mode="json", exclude={"event_hash"}),
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                if hashlib.sha256(canonical.encode()).hexdigest() != event.event_hash:
                    return False
                previous_hash = event.event_hash
        return True

    def enqueue_outbox(self, topic: str, payload: dict[str, object]) -> OutboxMessage:
        message = OutboxMessage(topic=topic, payload=payload)
        message_id = str(message.id)
        with self._lock:
            self.outbox[message_id] = message
            self.outbox_delivery[message_id] = OutboxDeliveryState(message_id=message_id)
        return message

    def get_outbox_delivery_state(self, message_id: str) -> OutboxDeliveryState | None:
        with self._lock:
            state = self.outbox_delivery.get(message_id)
            return replace(state) if state is not None else None

    def _outbox_due_at(self, message: OutboxMessage) -> datetime:
        state = self.outbox_delivery[str(message.id)]
        due_at = state.next_attempt_at or message.created_at
        return ensure_utc(due_at)

    def pending_outbox(
        self,
        limit: int = 100,
        *,
        now: datetime | None = None,
    ) -> list[OutboxMessage]:
        current = ensure_utc(now or datetime.now(UTC))
        with self._lock:
            pending: list[OutboxMessage] = []
            for message_id, message in self.outbox.items():
                state = self.outbox_delivery.setdefault(
                    message_id,
                    OutboxDeliveryState(message_id=message_id),
                )
                retry_at = ensure_utc(state.next_attempt_at) if state.next_attempt_at else None
                if message.sent_at is not None or state.dead_lettered_at is not None:
                    continue
                if retry_at is not None and retry_at > current:
                    continue
                pending.append(message)
            pending.sort(key=self._outbox_due_at)
            return pending[:limit]

    def dead_lettered_outbox(self, limit: int = 100) -> list[OutboxMessage]:
        with self._lock:
            rows = [
                message
                for message_id, message in self.outbox.items()
                if self.outbox_delivery.get(message_id) is not None
                and self.outbox_delivery[message_id].dead_lettered_at is not None
                and message.sent_at is None
            ]
            rows.sort(
                key=lambda item: ensure_utc(
                    self.outbox_delivery[str(item.id)].dead_lettered_at or item.created_at
                ),
                reverse=True,
            )
            return rows[:limit]

    def mark_outbox_attempt(
        self,
        message_id: str,
        *,
        attempted_at: datetime | None = None,
    ) -> OutboxDeliveryState | None:
        with self._lock:
            if message_id not in self.outbox:
                return None
            state = self.outbox_delivery.setdefault(
                message_id,
                OutboxDeliveryState(message_id=message_id),
            )
            state.attempt_count += 1
            state.last_attempt_at = ensure_utc(attempted_at or datetime.now(UTC))
            state.next_attempt_at = None
            return replace(state)

    def mark_outbox_failed(
        self,
        message_id: str,
        *,
        error: str,
        next_attempt_at: datetime | None,
        dead_lettered_at: datetime | None = None,
    ) -> OutboxDeliveryState | None:
        with self._lock:
            if message_id not in self.outbox:
                return None
            state = self.outbox_delivery.setdefault(
                message_id,
                OutboxDeliveryState(message_id=message_id),
            )
            state.last_error = error
            state.next_attempt_at = ensure_utc(next_attempt_at) if next_attempt_at else None
            state.dead_lettered_at = (
                ensure_utc(dead_lettered_at) if dead_lettered_at is not None else None
            )
            return replace(state)

    def requeue_outbox(self, message_id: str) -> bool:
        with self._lock:
            message = self.outbox.get(message_id)
            if message is None or message.sent_at is not None:
                return False
            state = self.outbox_delivery.setdefault(
                message_id,
                OutboxDeliveryState(message_id=message_id),
            )
            state.attempt_count = 0
            state.last_attempt_at = None
            state.next_attempt_at = datetime.now(UTC)
            state.last_error = None
            state.dead_lettered_at = None
            return True

    def mark_outbox_sent(self, message_id: str) -> None:
        with self._lock:
            message = self.outbox.get(message_id)
            if message is not None:
                message.sent_at = datetime.now(UTC)
                state = self.outbox_delivery.setdefault(
                    message_id,
                    OutboxDeliveryState(message_id=message_id),
                )
                state.next_attempt_at = None
                state.dead_lettered_at = None

    def health(self) -> bool:
        return True

    def close(self) -> None:
        return None
