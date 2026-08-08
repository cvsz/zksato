from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from zksato.config import Settings
from zksato.domain import AlertRule, AuditEvent, OrderRecord, OutboxMessage, Quote, Signal
from zksato.store import StateStore

metadata = MetaData()

orders_table = Table(
    "orders",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("broker_order_id", String(128), index=True),
    Column("client_order_id", String(128), unique=True, index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
quotes_table = Table(
    "quotes",
    metadata,
    Column("symbol", String(32), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
signals_table = Table(
    "signals",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
audit_table = Table(
    "audit_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
alerts_table = Table(
    "alerts",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("payload", JSON, nullable=False),
)
idempotency_table = Table(
    "idempotency_keys",
    metadata,
    Column("client_order_id", String(128), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
outbox_table = Table(
    "outbox",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("topic", String(128), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True)),
)


class SqlStateStore(StateStore):
    """SQL-backed state store with PostgreSQL-safe idempotency constraints."""

    def __init__(self, database_url: str, history_size: int = 1000) -> None:
        super().__init__(history_size=history_size)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        metadata.create_all(self.engine)
        self._load()

    def _load(self) -> None:
        with self.engine.connect() as conn:
            for payload in conn.execute(
                select(quotes_table.c.payload).order_by(quotes_table.c.symbol)
            ).scalars():
                quote = Quote.model_validate(payload)
                self.quotes[quote.symbol] = quote
                self.price_history[quote.symbol] = deque(
                    [quote.last], maxlen=self._history_size
                )
            for payload in conn.execute(
                select(orders_table.c.payload).order_by(orders_table.c.created_at)
            ).scalars():
                self.orders.append(OrderRecord.model_validate(payload))
            signal_payloads = list(
                conn.execute(
                    select(signals_table.c.payload)
                    .order_by(signals_table.c.created_at.desc())
                    .limit(self._history_size)
                ).scalars()
            )
            for payload in reversed(signal_payloads):
                self.signals.append(Signal.model_validate(payload))
            audit_payloads = list(
                conn.execute(
                    select(audit_table.c.payload)
                    .order_by(audit_table.c.created_at.desc())
                    .limit(self._history_size)
                ).scalars()
            )
            for payload in reversed(audit_payloads):
                self.audit.append(AuditEvent.model_validate(payload))
            for payload in conn.execute(select(alerts_table.c.payload)).scalars():
                alert = AlertRule.model_validate(payload)
                self.alerts[str(alert.id)] = alert
            self._client_order_ids.update(
                conn.execute(select(idempotency_table.c.client_order_id)).scalars()
            )
            for row in conn.execute(select(outbox_table)).mappings():
                message = OutboxMessage(
                    id=row["id"],
                    topic=row["topic"],
                    payload=row["payload"],
                    created_at=row["created_at"],
                    sent_at=row["sent_at"],
                )
                self.outbox[str(message.id)] = message

    def _upsert_payload(
        self,
        table: Table,
        key_column: Column[object],
        key: str,
        values: dict[str, object],
    ) -> None:
        with self.engine.begin() as conn:
            exists = conn.execute(select(key_column).where(key_column == key)).first()
            if exists:
                conn.execute(update(table).where(key_column == key).values(**values))
            else:
                conn.execute(insert(table).values(**values))

    def update_quote(self, quote: Quote) -> Quote:
        stored = super().update_quote(quote)
        if stored.timestamp != quote.timestamp:
            return stored
        self._upsert_payload(
            quotes_table,
            quotes_table.c.symbol,
            quote.symbol,
            {
                "symbol": quote.symbol,
                "payload": quote.model_dump(mode="json"),
                "updated_at": quote.timestamp,
            },
        )
        return quote

    def upsert_order(self, order: OrderRecord) -> OrderRecord:
        super().upsert_order(order)
        self._upsert_payload(
            orders_table,
            orders_table.c.id,
            str(order.id),
            {
                "id": str(order.id),
                "broker_order_id": order.broker_order_id,
                "client_order_id": order.client_order_id,
                "payload": order.model_dump(mode="json"),
                "created_at": order.created_at,
                "updated_at": order.updated_at,
            },
        )
        return order

    def claim_client_order_id(self, client_order_id: str) -> bool:
        now = datetime.now(UTC)
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(idempotency_table).values(
                        client_order_id=client_order_id,
                        created_at=now,
                    )
                )
        except IntegrityError:
            return False
        with self._lock:
            self._client_order_ids.add(client_order_id)
        return True

    def release_client_order_id(self, client_order_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                delete(idempotency_table).where(
                    idempotency_table.c.client_order_id == client_order_id
                )
            )
        super().release_client_order_id(client_order_id)

    def add_signal(self, signal: Signal) -> Signal:
        super().add_signal(signal)
        with self.engine.begin() as conn:
            conn.execute(
                insert(signals_table).values(
                    id=str(signal.id),
                    payload=signal.model_dump(mode="json"),
                    created_at=signal.timestamp,
                )
            )
        return signal

    def add_alert(self, alert: AlertRule) -> AlertRule:
        super().add_alert(alert)
        self._upsert_payload(
            alerts_table,
            alerts_table.c.id,
            str(alert.id),
            {"id": str(alert.id), "payload": alert.model_dump(mode="json")},
        )
        return alert

    def delete_alert(self, alert_id: str) -> bool:
        deleted = super().delete_alert(alert_id)
        with self.engine.begin() as conn:
            conn.execute(delete(alerts_table).where(alerts_table.c.id == alert_id))
        return deleted

    def add_audit(
        self,
        event_type: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> AuditEvent:
        event = super().add_audit(event_type, message, data)
        with self.engine.begin() as conn:
            conn.execute(
                insert(audit_table).values(
                    id=str(event.id),
                    payload=event.model_dump(mode="json"),
                    created_at=event.timestamp,
                )
            )
        return event

    def enqueue_outbox(self, topic: str, payload: dict[str, object]) -> OutboxMessage:
        message = super().enqueue_outbox(topic, payload)
        with self.engine.begin() as conn:
            conn.execute(
                insert(outbox_table).values(
                    id=str(message.id),
                    topic=message.topic,
                    payload=message.payload,
                    created_at=message.created_at,
                    sent_at=None,
                )
            )
        return message

    def mark_outbox_sent(self, message_id: str) -> None:
        super().mark_outbox_sent(message_id)
        sent_at = datetime.now(UTC)
        with self.engine.begin() as conn:
            conn.execute(
                update(outbox_table)
                .where(outbox_table.c.id == message_id)
                .values(sent_at=sent_at)
            )

    def health(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def close(self) -> None:
        self.engine.dispose()


def build_store(settings: Settings) -> StateStore:
    if settings.database_url:
        return SqlStateStore(settings.database_url)
    return StateStore()
