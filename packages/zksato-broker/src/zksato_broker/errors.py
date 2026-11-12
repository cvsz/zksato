"""Error classification and retry policies for broker adapters."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Any


class BrokerErrorCategory(str, Enum):
    """Categories of broker errors for retry policy decisions."""
    
    TRANSIENT = "transient"           # Retry with backoff
    RATE_LIMITED = "rate_limited"     # Retry after delay
    AUTH_FAILED = "auth_failed"       # Re-authenticate
    INVALID_ORDER = "invalid_order"   # Don't retry, fix order
    REJECTED = "rejected"             # Order rejected by exchange
    UNKNOWN = "unknown"               # Alert, manual intervention


@dataclass
class RetryPolicy:
    """Retry policy for a specific error category."""
    
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number (0-indexed)."""
        if attempt >= self.max_attempts:
            return 0.0
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay *= (0.5 + random.random())
        return delay


class BrokerError(Exception):
    """Base exception for broker errors with classification."""
    
    def __init__(
        self,
        message: str,
        category: BrokerErrorCategory = BrokerErrorCategory.UNKNOWN,
        original_error: Exception | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.original_error = original_error
        self.retry_after = retry_after


class BrokerConnectionError(BrokerError):
    """Broker connection error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.TRANSIENT, original_error)


class BrokerAuthenticationError(BrokerError):
    """Broker authentication error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.AUTH_FAILED, original_error)


class BrokerRateLimitError(BrokerError):
    """Broker rate limit error."""
    def __init__(self, message: str, retry_after: float | None = None, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.RATE_LIMITED, original_error, retry_after)


class BrokerInvalidOrderError(BrokerError):
    """Invalid order error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.INVALID_ORDER, original_error)


class BrokerRejectedError(BrokerError):
    """Order rejected by broker."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.REJECTED, original_error)


class BrokerUnknownError(BrokerError):
    """Unknown broker error."""
    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message, BrokerErrorCategory.UNKNOWN, original_error)


# Default retry policies per error category
RETRY_POLICIES: dict[BrokerErrorCategory, RetryPolicy] = {
    BrokerErrorCategory.TRANSIENT: RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0),
    BrokerErrorCategory.RATE_LIMITED: RetryPolicy(max_attempts=5, base_delay=5.0, max_delay=60.0),
    BrokerErrorCategory.AUTH_FAILED: RetryPolicy(max_attempts=1, base_delay=0, max_delay=0),
    BrokerErrorCategory.INVALID_ORDER: RetryPolicy(max_attempts=0),
    BrokerErrorCategory.REJECTED: RetryPolicy(max_attempts=0),
    BrokerErrorCategory.UNKNOWN: RetryPolicy(max_attempts=1, base_delay=10.0, max_delay=10.0),
}


def classify_error(error: Exception, broker: str) -> BrokerError:
    """Classify broker errors for consistent handling.
    
    Args:
        error: The original exception
        broker: Name of the broker (for context)
        
    Returns:
        Classified BrokerError with appropriate category and retry policy
    """
    error_str = str(error).lower()
    
    # Network/connection errors
    if any(keyword in error_str for keyword in ["timeout", "connection", "network", "dns", "unreachable"]):
        return BrokerConnectionError(str(error), error)
    
    # Rate limiting
    if any(keyword in error_str for keyword in ["rate limit", "429", "too many requests", "throttle"]):
        # Try to extract retry-after
        import re
        retry_after = None
        match = re.search(r"retry.?after[:\s]+(\d+)", error_str)
        if match:
            retry_after = float(match.group(1))
        return BrokerRateLimitError(str(error), retry_after=retry_after, original_error=error)
    
    # Authentication errors
    if any(keyword in error_str for keyword in ["unauthorized", "401", "authentication", "invalid token", "invalid api key", "invalid secret"]):
        return BrokerAuthenticationError(str(error), error)
    
    # Invalid order
    if any(keyword in error_str for keyword in ["invalid order", "bad request", "400", "malformed", "missing required", "invalid parameter"]):
        return BrokerInvalidOrderError(str(error), error)
    
    # Rejected orders
    if any(keyword in error_str for keyword in ["rejected", "reject", "insufficient", "margin", "not enough", "exceeds limit"]):
        return BrokerRejectedError(str(error), error)
    
    # Unknown
    return BrokerUnknownError(str(error), error)


def should_retry(error: BrokerError, attempt: int) -> tuple[bool, float]:
    """Determine if an error should be retried and the delay.
    
    Args:
        error: The classified broker error
        attempt: Current attempt number (0-indexed)
        
    Returns:
        Tuple of (should_retry, delay_seconds)
    """
    policy = RETRY_POLICIES.get(error.category, RETRY_POLICIES[BrokerErrorCategory.UNKNOWN])
    
    if attempt >= policy.max_attempts:
        return False, 0.0
    
    if error.category == BrokerErrorCategory.AUTH_FAILED and attempt == 0:
        # For auth failures, allow one retry after re-authentication
        return True, 0.0
    
    delay = policy.get_delay(attempt)
    return True, delay