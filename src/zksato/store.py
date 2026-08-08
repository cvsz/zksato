from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import RLock

from zksato.domain import AlertRule, AuditEvent, OrderRecord, Quote, Signal


class StateStore:
    """Thread-safe process-local state used by the paper runtime.

    The interfaces are intentionally small so PostgreSQL/Redis adapters can replace this
    store without changing the trading engines.
    """

    def __init__(self, history_size: int = 1000) -> None:
        self._lock = RLock()
        self.quotes: dict[str, Quote] = {}
        self.price_history: dict[str, deque[float]] = {}
        self.orders: list[OrderRecord] = []
        self.signals: deque[Signal] = deque(maxlen=history_size)
        self.audit: deque[AuditEvent] = deque(maxlen=history_size)
        self.alerts: dict[str, AlertRule] = {}
        self._history_size = history_size

    def update_quote(self, quote: Quote) -> Quote:
        with self._lock:
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

    def add_order(self, order: OrderRecord) -> OrderRecord:
        with self._lock:
            self.orders.append(order)
            return order

    def list_orders(self) -> list[OrderRecord]:
        with self._lock:
            return list(reversed(self.orders))

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
        event = AuditEvent(
            event_type=event_type,
            message=message,
            data=data or {},
            timestamp=datetime.now(UTC),
        )
        with self._lock:
            self.audit.append(event)
        return event

    def list_audit(self, limit: int = 100) -> list[AuditEvent]:
        with self._lock:
            return list(reversed(self.audit))[:limit]
