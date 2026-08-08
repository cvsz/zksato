from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

from zksato.domain import OrderIntent

approval_metadata = MetaData()
approvals_table = Table(
    "live_approvals",
    approval_metadata,
    Column("id", String(36), primary_key=True),
    Column("fingerprint", String(64), nullable=False, index=True),
    Column("intent", JSON, nullable=False),
    Column("created_by", String(128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("consumed_at", DateTime(timezone=True)),
    Column("consumed_by", String(128)),
)


class LiveApproval(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    fingerprint: str
    intent: dict[str, object]
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    consumed_at: datetime | None = None
    consumed_by: str | None = None

    @property
    def active(self) -> bool:
        return self.consumed_at is None and self.expires_at > datetime.now(UTC)


class ApprovalRequest(BaseModel):
    intent: OrderIntent
    ttl_seconds: int | None = Field(default=None, ge=15, le=3600)


def order_fingerprint(intent: OrderIntent) -> str:
    payload = json.dumps(intent.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class ApprovalRepository:
    """One-time intent-bound live approval repository."""

    def __init__(self, database_url: str | None = None) -> None:
        self._lock = RLock()
        self._items: dict[str, LiveApproval] = {}
        self.engine: Engine | None = None
        if database_url:
            connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
            self.engine = create_engine(
                database_url,
                future=True,
                pool_pre_ping=True,
                connect_args=connect_args,
            )
            approval_metadata.create_all(self.engine)

    def create(
        self,
        intent: OrderIntent,
        *,
        created_by: str,
        ttl_seconds: int,
    ) -> LiveApproval:
        now = datetime.now(UTC)
        approval = LiveApproval(
            fingerprint=order_fingerprint(intent),
            intent=intent.model_dump(mode="json"),
            created_by=created_by,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        if self.engine is None:
            with self._lock:
                self._items[str(approval.id)] = approval
            return approval
        with self.engine.begin() as conn:
            conn.execute(
                insert(approvals_table).values(
                    id=str(approval.id),
                    fingerprint=approval.fingerprint,
                    intent=approval.intent,
                    created_by=approval.created_by,
                    created_at=approval.created_at,
                    expires_at=approval.expires_at,
                )
            )
        return approval

    def get(self, approval_id: str) -> LiveApproval | None:
        if self.engine is None:
            with self._lock:
                return self._items.get(approval_id)
        with self.engine.connect() as conn:
            row = conn.execute(
                select(approvals_table).where(approvals_table.c.id == approval_id)
            ).mappings().first()
        return self._from_row(row) if row else None

    def list_recent(self, limit: int = 100) -> list[LiveApproval]:
        if self.engine is None:
            with self._lock:
                rows = sorted(
                    self._items.values(),
                    key=lambda item: item.created_at,
                    reverse=True,
                )
                return rows[:limit]
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(approvals_table)
                .order_by(approvals_table.c.created_at.desc())
                .limit(limit)
            ).mappings()
            return [self._from_row(row) for row in rows]

    def consume(
        self,
        approval_id: str,
        intent: OrderIntent,
        *,
        consumed_by: str,
        require_distinct_approver: bool,
    ) -> LiveApproval:
        expected = order_fingerprint(intent)
        now = datetime.now(UTC)
        if self.engine is None:
            with self._lock:
                approval = self._items.get(approval_id)
                self._validate(
                    approval,
                    expected,
                    now,
                    consumed_by,
                    require_distinct_approver,
                )
                assert approval is not None
                approval.consumed_at = now
                approval.consumed_by = consumed_by
                return approval
        with self.engine.begin() as conn:
            row = conn.execute(
                select(approvals_table).where(approvals_table.c.id == approval_id)
            ).mappings().first()
            approval = self._from_row(row) if row else None
            self._validate(
                approval,
                expected,
                now,
                consumed_by,
                require_distinct_approver,
            )
            result = conn.execute(
                update(approvals_table)
                .where(approvals_table.c.id == approval_id)
                .where(approvals_table.c.consumed_at.is_(None))
                .values(consumed_at=now, consumed_by=consumed_by)
            )
            if result.rowcount != 1:
                raise ValueError("live approval was already consumed")
            assert approval is not None
            approval.consumed_at = now
            approval.consumed_by = consumed_by
            return approval

    @staticmethod
    def _validate(
        approval: LiveApproval | None,
        expected_fingerprint: str,
        now: datetime,
        consumed_by: str,
        require_distinct_approver: bool,
    ) -> None:
        if approval is None:
            raise ValueError("live approval not found")
        expires_at = approval.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if approval.consumed_at is not None:
            raise ValueError("live approval was already consumed")
        if expires_at <= now:
            raise ValueError("live approval expired")
        if approval.fingerprint != expected_fingerprint:
            raise ValueError("live approval does not match order intent")
        if require_distinct_approver and approval.created_by == consumed_by:
            raise ValueError("live approval requires a distinct approver and executor")

    @staticmethod
    def _from_row(row: object) -> LiveApproval:
        mapping = row
        return LiveApproval(
            id=mapping["id"],  # type: ignore[index]
            fingerprint=mapping["fingerprint"],  # type: ignore[index]
            intent=mapping["intent"],  # type: ignore[index]
            created_by=mapping["created_by"],  # type: ignore[index]
            created_at=mapping["created_at"],  # type: ignore[index]
            expires_at=mapping["expires_at"],  # type: ignore[index]
            consumed_at=mapping["consumed_at"],  # type: ignore[index]
            consumed_by=mapping["consumed_by"],  # type: ignore[index]
        )

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
