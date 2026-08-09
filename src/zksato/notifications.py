from __future__ import annotations

import asyncio
from contextlib import suppress

import httpx

from zksato.store import StateStore


class OutboxDispatcher:
    """Retries durable notification outbox messages without blocking trading paths."""

    def __init__(self, store: StateStore, webhook_url: str | None, interval: float = 2.0) -> None:
        self.store = store
        self.webhook_url = webhook_url
        self.interval = interval
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
        async with httpx.AsyncClient(timeout=5) as client:
            for message in self.store.pending_outbox(50):
                try:
                    response = await client.post(self.webhook_url, json=message.payload)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    self.store.add_audit(
                        "notification.failed",
                        str(exc),
                        {"outbox_id": str(message.id)},
                    )
                    # A single poison or temporarily failing message must not head-of-line block
                    # unrelated notifications in the same batch. It remains unsent and durable
                    # for the next retry pass.
                    continue
                self.store.mark_outbox_sent(str(message.id))
                sent += 1
        return sent

    async def _run(self) -> None:
        while True:
            await self.flush_once()
            await asyncio.sleep(self.interval)
