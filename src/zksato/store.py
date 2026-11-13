from __future__ import annotations

import hashlib
import json
import secrets
from collections import deque
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    pass

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

    def __init__(self, history_size: int = 1000, max_orders: int = 10_000) -> None:
        self._lock = RLock()
        self.quotes: dict[str, Quote] = {}
        self.price_history: dict[str, deque[float]] = {}
        self.orders: list[OrderRecord] = []
        # Order indexes for O(1) lookups
        self._order_by_id: dict[UUID, OrderRecord] = {}
        self._order_by_client_id: dict[str, OrderRecord] = {}
        self._order_by_broker_id: dict[str, OrderRecord] = {}
        self._max_orders = max_orders
        self._archived_order_count: int = 0
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
        self.runtime_state: dict[str, dict[str, object]] = {}
        self.paper_account: dict[str, object] | None = None
        self._client_order_ids: set[str] = set()
        self._history_size = history_size
        self._broker_reconciliation_ready = False
        # Agent-native trading (AI-Trader compatible)
        self._agents: dict[UUID, dict[str, Any]] = {}
        self._agent_messages: dict[str, list[dict[str, Any]]] = {}
        self._agent_tasks: dict[str, list[dict[str, Any]]] = {}

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
            # Update indexes for existing order
            if order.id in self._order_by_id:
                # Remove old indexes
                old_order = self._order_by_id[order.id]
                if old_order.client_order_id:
                    self._order_by_client_id.pop(old_order.client_order_id, None)
                if old_order.broker_order_id:
                    self._order_by_broker_id.pop(old_order.broker_order_id, None)
                # Update in list
                for index, existing in enumerate(self.orders):
                    if existing.id == order.id:
                        self.orders[index] = order
                        break
            else:
                self.orders.append(order)

            # Add new indexes
            self._order_by_id[order.id] = order
            if order.client_order_id:
                self._order_by_client_id[order.client_order_id] = order
            if order.broker_order_id:
                self._order_by_broker_id[order.broker_order_id] = order

            # Archive oldest orders if exceeding max to prevent unbounded growth
            if len(self.orders) > self._max_orders:
                overflow = len(self.orders) - self._max_orders
                self._archived_order_count += overflow
                # Remove archived orders from indexes
                for archived in self.orders[:overflow]:
                    self._order_by_id.pop(archived.id, None)
                    if archived.client_order_id:
                        self._order_by_client_id.pop(archived.client_order_id, None)
                    if archived.broker_order_id:
                        self._order_by_broker_id.pop(archived.broker_order_id, None)
                self.orders = self.orders[overflow:]
            return order

    def list_orders(self) -> list[OrderRecord]:
        with self._lock:
            return list(reversed(self.orders))

    def order_count(self) -> int:
        with self._lock:
            return len(self.orders) + self._archived_order_count

    def find_order(self, order_id: str) -> OrderRecord | None:
        with self._lock:
            # Try UUID first
            try:
                uid = UUID(order_id)
                return self._order_by_id.get(uid)
            except ValueError:
                pass
            # Fall back to broker_order_id
            return self._order_by_broker_id.get(order_id)

    def find_order_by_client_order_id(self, client_order_id: str) -> OrderRecord | None:
        with self._lock:
            return self._order_by_client_id.get(client_order_id)

    def find_order_by_broker_order_id(self, broker_order_id: str) -> OrderRecord | None:
        with self._lock:
            return self._order_by_broker_id.get(broker_order_id)

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
            return int(
                sum(
                    item.quantity
                    for item in self.fills
                    if item.order_id is not None and str(item.order_id) == order_id
                )
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
            # Also reject if any existing order already uses this client_order_id
            # (defense in depth for restart durability when orders are persisted).
            if any(order.client_order_id == client_order_id for order in self.orders):
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

    @staticmethod
    def _normalize_runtime_state_key(key: str) -> str:
        if not isinstance(key, str):
            raise TypeError("runtime state key must be a string")
        normalized = key.strip()
        if not normalized:
            raise ValueError("runtime state key cannot be empty")
        if len(normalized) > 128:
            raise ValueError("runtime state key cannot exceed 128 characters")
        return normalized

    def save_runtime_state(self, key: str, payload: dict[str, object]) -> None:
        normalized = self._normalize_runtime_state_key(key)
        if not isinstance(payload, dict):
            raise TypeError("runtime state payload must be a dictionary")
        with self._lock:
            self.runtime_state[normalized] = deepcopy(payload)

    def get_runtime_state(self, key: str) -> dict[str, object] | None:
        normalized = self._normalize_runtime_state_key(key)
        with self._lock:
            payload = self.runtime_state.get(normalized)
            return deepcopy(payload) if payload is not None else None

    def delete_runtime_state(self, key: str) -> bool:
        normalized = self._normalize_runtime_state_key(key)
        with self._lock:
            return self.runtime_state.pop(normalized, None) is not None

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

    # ── Agent Management ──────────────────────────────────────────

    def find_agent_by_name(self, name: str) -> dict[str, Any] | None:
        """Find agent by name (exact match, then normalized)."""
        raw_name = name or ""
        normalized = raw_name.strip()
        if not normalized:
            return None
        with self._lock:
            for agent in self._agents.values():
                if agent.get("name") == raw_name or agent.get("name") == normalized:
                    return {
                        "id": str(agent.get("id")),
                        "name": agent.get("name"),
                        "email": agent.get("email"),
                        "password_hash": agent.get("password_hash"),
                        "wallet_address": agent.get("wallet_address"),
                        "cash": agent.get("cash"),
                        "deposited": agent.get("deposited"),
                        "points": agent.get("points"),
                        "reputation_score": agent.get("reputation_score"),
                        "identity_status": agent.get("identity_status"),
                        "is_verified": agent.get("is_verified"),
                        "role": agent.get("role"),
                    }
        return None

    def create_agent(self, agent_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new agent sub-account."""
        uid = UUID(str(agent_data["id"]))
        with self._lock:
            self._agents[uid] = dict(agent_data)
            # Persist to audit log
            self.add_audit(
                "agent_registered",
                f"agent registered: {agent_data['name']}",
                {
                    "agent_id": str(agent_data["id"]),
                    "name": agent_data["name"],
                    "email": agent_data.get("email"),
                    "wallet_address": agent_data.get("wallet_address"),
                    "initial_cash": agent_data.get("cash"),
                },
            )
            return dict(agent_data)

    def get_agent_by_id(self, agent_id: str | UUID) -> dict[str, Any] | None:
        """Get agent by UUID."""
        try:
            uid = UUID(str(agent_id))
        except ValueError:
            return None
        with self._lock:
            return self._agents.get(uid)

    def generate_agent_token(self, agent_id: str | UUID) -> str:
        """Generate a new API token for an agent."""
        uid = UUID(str(agent_id))
        token = secrets.token_urlsafe(32)
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            agent["token"] = token
            agent["updated_at"] = datetime.now(UTC)
        return token

    def get_or_issue_agent_token(self, agent_id: str | UUID) -> str:
        """Return the current agent API token, issuing one if empty."""
        uid = UUID(str(agent_id))
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            token = agent.get("token")
            if isinstance(token, str) and token:
                return token
            token = secrets.token_urlsafe(32)
            agent["token"] = token
            agent["updated_at"] = datetime.now(UTC)
            return token

    def update_agent_cash(self, agent_id: str | UUID, cash: float, deposited: float) -> None:
        """Update agent cash and deposited amounts."""
        uid = UUID(str(agent_id))
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            agent["cash"] = cash
            agent["deposited"] = deposited
            agent["updated_at"] = datetime.now(UTC)

    def get_agent_points(self, agent_id: str | UUID) -> int:
        """Get agent's points balance."""
        uid = UUID(str(agent_id))
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            points = agent.get("points", 0)
            return int(points) if isinstance(points, (int, float)) else 0

    def add_agent_points(
        self,
        agent_id: str | UUID,
        points: int,
        reason: str = "reward",
        *,
        source_type: str | None = None,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add points to an agent's account."""
        uid = UUID(str(agent_id))
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            agent["points"] = int(agent.get("points", 0)) + points
            agent["updated_at"] = datetime.now(UTC)
            self.add_audit(
                "agent_points_added",
                f"points added to agent {agent.get('name')}",
                {
                    "agent_id": str(agent_id),
                    "points": points,
                    "reason": reason,
                    "source_type": source_type,
                    "source_id": source_id,
                    "metadata": metadata,
                },
            )

    def create_position(
        self,
        agent_id: str | UUID,
        symbol: str,
        market: str,
        side: str,
        quantity: float,
        entry_price: float,
    ) -> None:
        """Create a position for an agent."""
        uid = UUID(str(agent_id))
        with self._lock:
            agent = self._agents.get(uid)
            if agent is None:
                raise ValueError("Agent not found")
            if "_positions" not in agent:
                agent["_positions"] = []
            agent["_positions"].append(
                {
                    "symbol": symbol,
                    "market": market,
                    "side": side,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "current_price": entry_price,
                    "opened_at": datetime.now(UTC),
                }
            )
            agent["updated_at"] = datetime.now(UTC)

    def get_unread_agent_messages(
        self, agent_id: str | UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get unread agent messages."""
        agent_id_str = str(agent_id)
        with self._lock:
            messages = [
                m for m in self._agent_messages.get(agent_id_str, []) if not m.get("read", False)
            ]
            messages.sort(key=lambda m: m.get("created_at", ""), reverse=True)
            return messages[:limit]

    def mark_agent_messages_read(self, agent_id: str | UUID, message_ids: list[str]) -> int:
        """Mark agent messages as read."""
        agent_id_str = str(agent_id)
        with self._lock:
            updated = 0
            for m in self._agent_messages.get(agent_id_str, []):
                if str(m["id"]) in message_ids and not m.get("read", False):
                    m["read"] = True
                    updated += 1
            return updated

    def get_pending_agent_tasks(
        self, agent_id: str | UUID, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get pending agent tasks."""
        agent_id_str = str(agent_id)
        with self._lock:
            tasks = [
                t for t in self._agent_tasks.get(agent_id_str, []) if t.get("status") == "pending"
            ]
            tasks.sort(key=lambda t: t.get("created_at", ""))
            return tasks[:limit]

    def health(self) -> bool:
        return True

    def close(self) -> None:
        return None

    def _rebuild_order_indexes(self) -> None:
        """Rebuild order indexes from the orders list."""
        with self._lock:
            self._order_by_id.clear()
            self._order_by_client_id.clear()
            self._order_by_broker_id.clear()
            for order in self.orders:
                self._order_by_id[order.id] = order
                if order.client_order_id:
                    self._order_by_client_id[order.client_order_id] = order
                if order.broker_order_id:
                    self._order_by_broker_id[order.broker_order_id] = order
