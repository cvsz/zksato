from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


MAX_ERROR_LENGTH = 500


@dataclass(slots=True)
class OutboxDeliveryState:
    message_id: str
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    dead_lettered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetryPlan:
    next_attempt_at: datetime | None
    dead_lettered_at: datetime | None

    @property
    def dead_lettered(self) -> bool:
        return self.dead_lettered_at is not None


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def truncate_error(value: object, limit: int = MAX_ERROR_LENGTH) -> str:
    text = str(value).replace("\x00", "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def plan_retry(
    *,
    attempt_count: int,
    base_seconds: float,
    max_seconds: float,
    max_attempts: int,
    now: datetime | None = None,
) -> RetryPlan:
    """Return a deterministic bounded exponential retry/dead-letter decision.

    ``attempt_count`` is the number of delivery attempts already recorded, including
    the attempt that just failed. Once it reaches ``max_attempts`` the message moves
    to the dead-letter state and is no longer returned by the normal pending queue.
    """

    if attempt_count < 1:
        raise ValueError("attempt_count must be at least 1")
    if base_seconds <= 0 or max_seconds <= 0:
        raise ValueError("retry delays must be positive")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    current = ensure_utc(now or datetime.now(UTC))
    if attempt_count >= max_attempts:
        return RetryPlan(next_attempt_at=None, dead_lettered_at=current)

    exponent = min(attempt_count - 1, 30)
    delay_seconds = min(max_seconds, base_seconds * (2**exponent))
    return RetryPlan(
        next_attempt_at=current + timedelta(seconds=delay_seconds),
        dead_lettered_at=None,
    )
