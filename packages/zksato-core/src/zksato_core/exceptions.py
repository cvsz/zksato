"""Domain exceptions hierarchy."""

from __future__ import annotations

from typing import Any


class ZksatoError(Exception):
    """Base exception for all zksato errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class ConfigurationError(ZksatoError):
    """Configuration-related errors."""

    pass


class ValidationError(ZksatoError):
    """Input validation errors."""

    pass


class MarketDataError(ZksatoError):
    """Market data related errors."""

    pass


class StaleMarketDataError(MarketDataError):
    """Raised when market data is too stale for safe execution."""

    pass


class MarketClosedError(MarketDataError):
    """Raised when market session is closed."""

    pass


class BrokerError(ZksatoError):
    """Broker-related errors."""

    pass


class BrokerConnectionError(BrokerError):
    """Broker connection failures."""

    pass


class BrokerAuthenticationError(BrokerError):
    """Broker authentication failures."""

    pass


class OrderError(ZksatoError):
    """Order-related errors."""

    pass


class OrderRejectedError(OrderError):
    """Order was rejected by broker or risk engine."""

    pass


class OrderNotFoundError(OrderError):
    """Order not found."""

    pass


class OrderCancellationError(OrderError):
    """Order cancellation failed."""

    pass


class RiskError(ZksatoError):
    """Risk management errors."""

    pass


class RiskLimitExceededError(RiskError):
    """Risk limit exceeded."""

    pass


class KillSwitchActiveError(RiskError):
    """Global kill switch is active."""

    pass


class ReconciliationError(ZksatoError):
    """Reconciliation errors."""

    pass


class ReconciliationMismatchError(ReconciliationError):
    """Broker and local state mismatch."""

    pass


class ReconciliationRequiredError(ReconciliationError):
    """Reconciliation is required before proceeding."""

    pass


class StrategyError(ZksatoError):
    """Strategy-related errors."""

    pass


class StrategyNotFoundError(StrategyError):
    """Strategy not found."""

    pass


class BacktestError(StrategyError):
    """Backtest-related errors."""

    pass


class AuthenticationError(ZksatoError):
    """Authentication/authorization errors."""

    pass


class AuthorizationError(ZksatoError):
    """Authorization errors (insufficient permissions)."""

    pass


class SessionError(ZksatoError):
    """Session-related errors."""

    pass


class SessionExpiredError(SessionError):
    """Session has expired."""

    pass


class RateLimitError(ZksatoError):
    """Rate limit exceeded."""

    pass


class IdempotencyError(ZksatoError):
    """Idempotency key conflict."""

    pass


class PersistenceError(ZksatoError):
    """Database/persistence errors."""

    pass


class MigrationError(ZksatoError):
    """Database migration errors."""

    pass


class AgentError(ZksatoError):
    """Agent OS errors."""

    pass


class AgentSubAccountError(AgentError):
    """Sub-account errors."""

    pass


class AgentSkillError(AgentError):
    """Skill execution errors."""

    pass


class NotificationError(ZksatoError):
    """Notification delivery errors."""

    pass


class PredictionMarketError(ZksatoError):
    """Prediction market errors."""

    pass


class TFEXError(ZksatoError):
    """TFEX-specific errors."""

    pass


class TFEXContractError(TFEXError):
    """TFEX contract errors."""

    pass


class TFEXMarginError(TFEXError):
    """TFEX margin errors."""

    pass


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable."""
    retryable_types = (
        BrokerConnectionError,
        BrokerError,
        PersistenceError,
        RateLimitError,
        ReconciliationError,
    )
    return isinstance(error, retryable_types)


def is_fatal_error(error: Exception) -> bool:
    """Check if an error is fatal (should not retry)."""
    fatal_types = (
        ConfigurationError,
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        KillSwitchActiveError,
        OrderRejectedError,
        RiskLimitExceededError,
    )
    return isinstance(error, fatal_types)