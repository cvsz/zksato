from __future__ import annotations

import asyncio
from contextlib import suppress

import httpx

from zksato.config import get_settings
from zksato.outbox_delivery import plan_retry, truncate_error
from zksato.store import StateStore


def _safe_delivery_error(exc: Exception) -> str:
    """Return bounded diagnostic text without persisting webhook URLs or payload data."""

    if isinstance(exc, httpx.HTTPStatusError):
        return truncate_error(
            f"{type(exc).__name__}: status={exc.response.status_code}"
        )
    return truncate_error(type(exc).__name__)


class OutboxDispatcher:
    """Dispatch durable webhook notifications with bounded retry/dead-letter semantics."""

    def __init__(
        self,
        store: StateStore,
        webhook_url: str | None,
        *,
        interval: float | None = None,
        timeout_seconds: float | None = None,
        batch_size: int | None = None,
        retry_base_seconds: float | None = None,
        retry_max_seconds: float | None = None,
        max_attempts: int | None = None,
    ) -> None:
        settings = get_settings()
        self.store = store
        self.webhook_url = webhook_url
        self.interval = (
            interval
            if interval is not None
            else settings.notification_dispatch_interval_seconds
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.notification_timeout_seconds
        )
        self.batch_size = (
            batch_size if batch_size is not None else settings.notification_batch_size
        )
        self.retry_base_seconds = (
            retry_base_seconds
            if retry_base_seconds is not None
            else settings.notification_retry_base_seconds
        )
        self.retry_max_seconds = (
            retry_max_seconds
            if retry_max_seconds is not None
            else settings.notification_retry_max_seconds
        )
        self.max_attempts = (
            max_attempts if max_attempts is not None else settings.notification_max_attempts
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if not self.webhook_url:
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def flush_once(self) -> int:
        if not self.webhook_url:
            return 0
        sent = 0
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for message in self.store.pending_outbox(self.batch_size):
                message_id = str(message.id)
                attempt = self.store.mark_outbox_attempt(message_id)
                if attempt is None:
                    continue
                try:
                    response = await client.post(
                        self.webhook_url,
                        json=message.payload,
                        headers={"X-ZKSATO-Outbox-Id": message_id},
                    )
                    response.raise_for_status()
                except (httpx.HTTPError, TypeError, ValueError) as exc:
                    retry = plan_retry(
                        attempt_count=attempt.attempt_count,
                        base_seconds=self.retry_base_seconds,
                        max_seconds=self.retry_max_seconds,
                        max_attempts=self.max_attempts,
                    )
                    error = _safe_delivery_error(exc)
                    self.store.mark_outbox_failed(
                        message_id,
                        error=error,
                        next_attempt_at=retry.next_attempt_at,
                        dead_lettered_at=retry.dead_lettered_at,
                    )
                    event_type = (
                        "notification.dead_lettered"
                        if retry.dead_lettered
                        else "notification.retry_scheduled"
                    )
                    self.store.add_audit(
                        event_type,
                        error,
                        {
                            "outbox_id": message_id,
                            "attempt_count": attempt.attempt_count,
                            "next_attempt_at": (
                                retry.next_attempt_at.isoformat()
                                if retry.next_attempt_at is not None
                                else None
                            ),
                        },
                    )
                    # A poison or temporarily failing message cannot head-of-line block
                    # unrelated notifications. Retry eligibility is persisted separately.
                    continue
                self.store.mark_outbox_sent(message_id)
                sent += 1
        return sent

    async def _run(self) -> None:
        while True:
            await self.flush_once()
            await asyncio.sleep(self.interval)
