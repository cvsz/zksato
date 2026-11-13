"""Outbox delivery for zksato."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from zksato_core.models import OutboxMessage

from zksato_portfolio.persistence import PersistenceLayer


class OutboxDelivery:
    """Delivers outbox messages with retry logic."""

    def __init__(
        self,
        persistence: PersistenceLayer,
        handler: Callable[[OutboxMessage], Any],
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> None:
        self.persistence = persistence
        self.handler = handler
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the delivery loop."""
        self._running = True
        self._task = asyncio.create_task(self._delivery_loop())

    async def stop(self) -> None:
        """Stop the delivery loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _delivery_loop(self) -> None:
        while self._running:
            try:
                await self._process_batch()
            except Exception:
                pass  # Log in production
            await asyncio.sleep(1.0)

    async def _process_batch(self) -> None:
        messages = await self.persistence.get_pending_outbox(limit=100)

        for message in messages:
            if not self._running:
                break

            try:
                await self.handler(message)
                await self.persistence.mark_outbox_sent(str(message.id))
            except Exception as e:
                message.retry_count += 1
                message.last_error = str(e)
                if message.retry_count >= self.max_retries:
                    # Move to dead letter or alert
                    pass
                await asyncio.sleep(self.retry_delay)
