from __future__ import annotations

import hashlib
import json
from collections import deque
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
            history = self.price_history.setdefault(
                quote.symbol, deque(maxlen=self._history_size)
            )
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
        with self._lock:
            self.outbox[str(message.id)] = message
        return message

    def pending_outbox(self, limit: int = 100) -> list[OutboxMessage]:
        with self._lock:
            pending = [item for item in self.outbox.values() if item.sent_at is None]
            return sorted(pending, key=lambda item: item.created_at)[:limit]

    def mark_outbox_sent(self, message_id: str) -> None:
        with self._lock:
            message = self.outbox.get(message_id)
            if message is not None:
                message.sent_at = datetime.now(UTC)

    def health(self) -> bool:
        return True

    def close(self) -> None:
        return None
