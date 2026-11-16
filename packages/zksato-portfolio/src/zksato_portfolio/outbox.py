"""Outbox delivery for zksato."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from zksato_core.models import OutboxMessage

from zksato_portfolio.persistence import PersistenceLayer

logger = logging.getLogger(__name__)


class OutboxDelivery:
    """Delivers outbox messages with retry logic and dead-letter handling.

    Messages that exceed ``max_retries`` are dead-lettered (marked as
    ``dead_lettered_at``) so poison messages cannot block the delivery loop
    forever.  Delivery exceptions are logged rather than swallowed silently.
    """

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
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _delivery_loop(self) -> None:
        while self._running:
            try:
                await self._process_batch()
            except Exception as exc:  # log and continue; never kill the loop
                logger.exception("outbox batch failed: %s", exc)
            await asyncio.sleep(1.0)

    async def _process_batch(self) -> None:
        messages = await self.persistence.get_pending_outbox(limit=100)

        for message in messages:
            if not self._running:
                break

            try:
                await self.handler(message)
                await self.persistence.mark_outbox_sent(str(message.id))
            except Exception as exc:
                message.retry_count += 1
                message.last_error = str(exc)
                message.last_attempt_at = datetime.now(UTC)
                if message.retry_count >= self.max_retries:
                    # Dead-letter: stop retrying this poison message so it
                    # cannot block the delivery loop forever.
                    await self.persistence.mark_outbox_dead_lettered(str(message.id))
                    logger.error(
                        "outbox message %s dead-lettered after %d retries: %s",
                        message.id,
                        message.retry_count,
                        exc,
                    )
                else:
                    logger.warning(
                        "outbox message %s attempt %d failed: %s",
                        message.id,
                        message.retry_count,
                        exc,
                    )
                await asyncio.sleep(self.retry_delay)
