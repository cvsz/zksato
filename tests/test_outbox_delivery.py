from datetime import UTC, datetime, timedelta

import httpx
import pytest

from zksato.notifications import OutboxDispatcher
from zksato.outbox_delivery import ensure_utc, plan_retry, truncate_error
from zksato.persistence import SqlStateStore
from zksato.store import StateStore


def test_retry_plan_is_bounded_and_dead_letters() -> None:
    now = datetime(2026, 8, 9, 3, 0, tzinfo=UTC)

    first = plan_retry(
        attempt_count=1,
        base_seconds=5,
        max_seconds=30,
        max_attempts=4,
        now=now,
    )
    assert first.next_attempt_at == now + timedelta(seconds=5)
    assert first.dead_lettered is False

    third = plan_retry(
        attempt_count=3,
        base_seconds=20,
        max_seconds=30,
        max_attempts=4,
        now=now,
    )
    assert third.next_attempt_at == now + timedelta(seconds=30)

    terminal = plan_retry(
        attempt_count=4,
        base_seconds=5,
        max_seconds=30,
        max_attempts=4,
        now=now,
    )
    assert terminal.next_attempt_at is None
    assert terminal.dead_lettered_at == now


def test_store_schedules_dead_letters_and_requeues() -> None:
    store = StateStore()
    message = store.enqueue_outbox("risk.alert", {"symbol": "AOT"})
    message_id = str(message.id)
    attempted_at = datetime(2026, 8, 9, 3, 0, tzinfo=UTC)

    attempt = store.mark_outbox_attempt(message_id, attempted_at=attempted_at)
    assert attempt is not None
    assert attempt.attempt_count == 1

    retry_at = attempted_at + timedelta(seconds=10)
    store.mark_outbox_failed(
        message_id,
        error="temporary failure",
        next_attempt_at=retry_at,
    )
    assert store.pending_outbox(now=attempted_at + timedelta(seconds=9)) == []
    assert store.pending_outbox(now=retry_at) == [message]

    store.mark_outbox_attempt(message_id, attempted_at=retry_at)
    store.mark_outbox_failed(
        message_id,
        error="permanent failure",
        next_attempt_at=None,
        dead_lettered_at=retry_at,
    )
    assert store.pending_outbox(now=retry_at + timedelta(seconds=60)) == []
    assert store.dead_lettered_outbox() == [message]

    assert store.requeue_outbox(message_id) is True
    state = store.get_outbox_delivery_state(message_id)
    assert state is not None
    assert state.attempt_count == 0
    assert state.dead_lettered_at is None
    assert state.last_error is None
    assert store.pending_outbox(now=datetime.now(UTC) + timedelta(seconds=1)) == [message]


def test_sql_outbox_delivery_state_survives_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'outbox.db'}"
    attempted_at = datetime(2026, 8, 9, 3, 0, tzinfo=UTC)
    retry_at = attempted_at + timedelta(seconds=15)

    first = SqlStateStore(database_url)
    message = first.enqueue_outbox("system.health", {"ok": False})
    message_id = str(message.id)
    first.mark_outbox_attempt(message_id, attempted_at=attempted_at)
    first.mark_outbox_failed(
        message_id,
        error="endpoint unavailable",
        next_attempt_at=retry_at,
    )
    first.close()

    restarted = SqlStateStore(database_url)
    try:
        state = restarted.get_outbox_delivery_state(message_id)
        assert state is not None
        assert state.attempt_count == 1
        assert ensure_utc(state.last_attempt_at) == attempted_at
        assert ensure_utc(state.next_attempt_at) == retry_at
        assert state.last_error == "endpoint unavailable"
        assert restarted.pending_outbox(now=attempted_at + timedelta(seconds=1)) == []
        assert len(restarted.pending_outbox(now=retry_at)) == 1
    finally:
        restarted.close()


class _FailingAsyncClient:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def __aenter__(self) -> "_FailingAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        del args

    async def post(
        self,
        url: str,
        *,
        json: object,
        headers: dict[str, str],
    ) -> httpx.Response:
        del json, headers
        request = httpx.Request("POST", url)
        return httpx.Response(503, request=request)


@pytest.mark.asyncio
async def test_dispatcher_dead_letters_after_bounded_attempts(monkeypatch) -> None:
    monkeypatch.setattr("zksato.notifications.httpx.AsyncClient", _FailingAsyncClient)
    store = StateStore()
    message = store.enqueue_outbox("notification.test", {"hello": "world"})
    dispatcher = OutboxDispatcher(
        store,
        "https://example.invalid/webhook",
        timeout_seconds=1,
        batch_size=10,
        retry_base_seconds=1,
        retry_max_seconds=10,
        max_attempts=1,
    )

    assert await dispatcher.flush_once() == 0
    state = store.get_outbox_delivery_state(str(message.id))
    assert state is not None
    assert state.attempt_count == 1
    assert state.dead_lettered_at is not None
    assert store.dead_lettered_outbox() == [message]
    assert store.list_audit(1)[0].event_type == "notification.dead_lettered"


def test_error_truncation_is_bounded() -> None:
    value = truncate_error("x" * 800)
    assert len(value) == 500
    assert value.endswith("...")
