from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
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
from zksato.outbox_delivery import OutboxDeliveryState
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
order_events_table = Table(
    "order_events",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("order_id", String(36), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
fills_table = Table(
    "fills",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("broker_fill_id", String(128), unique=True, index=True),
    Column("order_id", String(36), index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
risk_evaluations_table = Table(
    "risk_evaluations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("client_order_id", String(128), index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
account_snapshots_table = Table(
    "account_snapshots",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
strategy_versions_table = Table(
    "strategy_versions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(64), nullable=False, index=True),
    Column("version", String(64), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("name", "version", name="uq_strategy_versions_name_version"),
)
strategy_runs_table = Table(
    "strategy_runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
bars_table = Table(
    "market_bars",
    metadata,
    Column("bar_key", String(160), primary_key=True),
    Column("symbol", String(32), nullable=False, index=True),
    Column("timeframe", String(16), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
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
    Column("attempt_count", Integer, nullable=False, default=0),
    Column("last_attempt_at", DateTime(timezone=True)),
    Column("next_attempt_at", DateTime(timezone=True)),
    Column("last_error", String(500)),
    Column("dead_lettered_at", DateTime(timezone=True)),
)
runtime_state_table = Table(
    "runtime_state",
    metadata,
    Column("key", String(128), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
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
                self.price_history[quote.symbol] = deque([quote.last], maxlen=self._history_size)
            for payload in conn.execute(
                select(orders_table.c.payload).order_by(orders_table.c.created_at)
            ).scalars():
                self.orders.append(OrderRecord.model_validate(payload))
            for payload in conn.execute(
                select(order_events_table.c.payload)
                .order_by(order_events_table.c.created_at.desc())
                .limit(self._history_size * 4)
            ).scalars():
                self.order_events.appendleft(OrderEvent.model_validate(payload))
            for payload in conn.execute(
                select(fills_table.c.payload)
                .order_by(fills_table.c.created_at.desc())
                .limit(self._history_size * 4)
            ).scalars():
                self.fills.appendleft(FillRecord.model_validate(payload))
            for payload in conn.execute(
                select(risk_evaluations_table.c.payload)
                .order_by(risk_evaluations_table.c.created_at.desc())
                .limit(self._history_size * 4)
            ).scalars():
                self.risk_evaluations.appendleft(RiskEvaluation.model_validate(payload))
            for payload in conn.execute(
                select(account_snapshots_table.c.payload)
                .order_by(account_snapshots_table.c.created_at.desc())
                .limit(self._history_size)
            ).scalars():
                self.account_snapshots.appendleft(AccountSnapshot.model_validate(payload))
            for payload in conn.execute(select(strategy_versions_table.c.payload)).scalars():
                version = StrategyVersion.model_validate(payload)
                self.strategy_versions[f"{version.name}:{version.version}"] = version
            for payload in conn.execute(
                select(strategy_runs_table.c.payload)
                .order_by(strategy_runs_table.c.created_at.desc())
                .limit(self._history_size * 2)
            ).scalars():
                self.strategy_runs.appendleft(StrategyRun.model_validate(payload))
            for payload in conn.execute(select(bars_table.c.payload)).scalars():
                bar = Bar.model_validate(payload)
                self.bars[self._bar_key(bar)] = bar
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
                message_id = str(row["id"])
                message = OutboxMessage(
                    id=row["id"],
                    topic=row["topic"],
                    payload=row["payload"],
                    created_at=row["created_at"],
                    sent_at=row["sent_at"],
                )
                self.outbox[message_id] = message
                self.outbox_delivery[message_id] = OutboxDeliveryState(
                    message_id=message_id,
                    attempt_count=int(row["attempt_count"] or 0),
                    last_attempt_at=row["last_attempt_at"],
                    next_attempt_at=row["next_attempt_at"],
                    last_error=row["last_error"],
                    dead_lettered_at=row["dead_lettered_at"],
                )
            paper_state = conn.execute(
                select(runtime_state_table.c.payload).where(
                    runtime_state_table.c.key == "paper_account"
                )
            ).scalar_one_or_none()
            if isinstance(paper_state, dict):
                self.paper_account = paper_state
            # Broker reconciliation readiness is deliberately NOT restored. It is a
            # freshness assertion about this process/session and must be established
            # by a successful broker snapshot after every restart.
            self._broker_reconciliation_ready = False

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

    def _persist_outbox_delivery_state(self, message_id: str) -> None:
        state = self.get_outbox_delivery_state(message_id)
        if state is None:
            return
        with self.engine.begin() as conn:
            conn.execute(
                update(outbox_table)
                .where(outbox_table.c.id == message_id)
                .values(
                    attempt_count=state.attempt_count,
                    last_attempt_at=state.last_attempt_at,
                    next_attempt_at=state.next_attempt_at,
                    last_error=state.last_error,
                    dead_lettered_at=state.dead_lettered_at,
                )
            )

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

    def add_order_event(self, event: OrderEvent) -> OrderEvent:
        super().add_order_event(event)
        with self.engine.begin() as conn:
            conn.execute(
                insert(order_events_table).values(
                    id=str(event.id),
                    order_id=str(event.order_id),
                    payload=event.model_dump(mode="json"),
                    created_at=event.timestamp,
                )
            )
        return event

    def add_fill(self, fill: FillRecord) -> FillRecord:
        existing = super().add_fill(fill)
        if existing.id != fill.id:
            return existing
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(fills_table).values(
                        id=str(fill.id),
                        broker_fill_id=fill.broker_fill_id,
                        order_id=str(fill.order_id) if fill.order_id else None,
                        payload=fill.model_dump(mode="json"),
                        created_at=fill.timestamp,
                    )
                )
        except IntegrityError:
            if fill.broker_fill_id:
                with self._lock:
                    return next(
                        item for item in self.fills if item.broker_fill_id == fill.broker_fill_id
                    )
            raise
        return fill

    def add_risk_evaluation(self, evaluation: RiskEvaluation) -> RiskEvaluation:
        super().add_risk_evaluation(evaluation)
        with self.engine.begin() as conn:
            conn.execute(
                insert(risk_evaluations_table).values(
                    id=str(evaluation.id),
                    client_order_id=evaluation.client_order_id,
                    payload=evaluation.model_dump(mode="json"),
                    created_at=evaluation.timestamp,
                )
            )
        return evaluation

    def add_account_snapshot(self, snapshot: AccountSnapshot) -> AccountSnapshot:
        super().add_account_snapshot(snapshot)
        with self.engine.begin() as conn:
            conn.execute(
                insert(account_snapshots_table).values(
                    id=str(snapshot.id),
                    payload=snapshot.model_dump(mode="json"),
                    created_at=snapshot.timestamp,
                )
            )
        return snapshot

    def add_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        stored = super().add_strategy_version(version)
        if stored.id != version.id:
            return stored
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(strategy_versions_table).values(
                        id=str(version.id),
                        name=version.name,
                        version=version.version,
                        payload=version.model_dump(mode="json"),
                        created_at=version.created_at,
                    )
                )
        except IntegrityError as exc:
            with self.engine.connect() as conn:
                payload = conn.execute(
                    select(strategy_versions_table.c.payload).where(
                        strategy_versions_table.c.name == version.name,
                        strategy_versions_table.c.version == version.version,
                    )
                ).scalar_one_or_none()
            if payload is None:
                raise
            existing = StrategyVersion.model_validate(payload)
            key = f"{existing.name}:{existing.version}"
            with self._lock:
                self.strategy_versions[key] = existing
            if existing.code_hash == version.code_hash and existing.config == version.config:
                return existing
            raise ValueError(f"strategy version {key} is immutable") from exc
        return version

    def add_strategy_run(self, run: StrategyRun) -> StrategyRun:
        super().add_strategy_run(run)
        self._upsert_payload(
            strategy_runs_table,
            strategy_runs_table.c.id,
            str(run.id),
            {
                "id": str(run.id),
                "payload": run.model_dump(mode="json"),
                "created_at": run.started_at,
            },
        )
        return run

    def upsert_bar(self, bar: Bar) -> Bar:
        super().upsert_bar(bar)
        key = self._bar_key(bar)
        self._upsert_payload(
            bars_table,
            bars_table.c.bar_key,
            key,
            {
                "bar_key": key,
                "symbol": bar.symbol,
                "timeframe": bar.timeframe,
                "payload": bar.model_dump(mode="json"),
                "created_at": bar.timestamp,
            },
        )
        return bar

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

    def set_broker_reconciliation_ready(self, ready: bool) -> None:
        # Freshness state is intentionally process-local. Persisting/restoring `true`
        # would allow a later process to inherit a stale broker snapshot assertion.
        super().set_broker_reconciliation_ready(ready)

    def save_paper_account(self, payload: dict[str, object]) -> None:
        super().save_paper_account(payload)
        self._upsert_payload(
            runtime_state_table,
            runtime_state_table.c.key,
            "paper_account",
            {
                "key": "paper_account",
                "payload": payload,
                "updated_at": datetime.now(UTC),
            },
        )

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
                    attempt_count=0,
                    last_attempt_at=None,
                    next_attempt_at=None,
                    last_error=None,
                    dead_lettered_at=None,
                )
            )
        return message

    def mark_outbox_attempt(
        self,
        message_id: str,
        *,
        attempted_at: datetime | None = None,
    ) -> OutboxDeliveryState | None:
        state = super().mark_outbox_attempt(message_id, attempted_at=attempted_at)
        if state is not None:
            self._persist_outbox_delivery_state(message_id)
        return state

    def mark_outbox_failed(
        self,
        message_id: str,
        *,
        error: str,
        next_attempt_at: datetime | None,
        dead_lettered_at: datetime | None = None,
    ) -> OutboxDeliveryState | None:
        state = super().mark_outbox_failed(
            message_id,
            error=error,
            next_attempt_at=next_attempt_at,
            dead_lettered_at=dead_lettered_at,
        )
        if state is not None:
            self._persist_outbox_delivery_state(message_id)
        return state

    def requeue_outbox(self, message_id: str) -> bool:
        requeued = super().requeue_outbox(message_id)
        if requeued:
            self._persist_outbox_delivery_state(message_id)
        return requeued

    def mark_outbox_sent(self, message_id: str) -> None:
        super().mark_outbox_sent(message_id)
        state = self.get_outbox_delivery_state(message_id)
        sent_at = self.outbox.get(message_id).sent_at if message_id in self.outbox else None
        with self.engine.begin() as conn:
            conn.execute(
                update(outbox_table)
                .where(outbox_table.c.id == message_id)
                .values(
                    sent_at=sent_at,
                    attempt_count=state.attempt_count if state else 0,
                    last_attempt_at=state.last_attempt_at if state else None,
                    next_attempt_at=state.next_attempt_at if state else None,
                    last_error=state.last_error if state else None,
                    dead_lettered_at=state.dead_lettered_at if state else None,
                )
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
