"""Tests for zksato-core exceptions module."""

from zksato_core.exceptions import (
    AgentError,
    AgentSkillError,
    AgentSubAccountError,
    AuthenticationError,
    AuthorizationError,
    BacktestError,
    BrokerAuthenticationError,
    BrokerConnectionError,
    BrokerError,
    ConfigurationError,
    IdempotencyError,
    KillSwitchActiveError,
    MarketClosedError,
    MarketDataError,
    MigrationError,
    NotificationError,
    OrderCancellationError,
    OrderError,
    OrderNotFoundError,
    OrderRejectedError,
    PersistenceError,
    PredictionMarketError,
    RateLimitError,
    ReconciliationError,
    ReconciliationMismatchError,
    ReconciliationRequiredError,
    RiskError,
    RiskLimitExceededError,
    SessionError,
    SessionExpiredError,
    StaleMarketDataError,
    StrategyError,
    StrategyNotFoundError,
    TFEXContractError,
    TFEXError,
    TFEXMarginError,
    ValidationError,
    ZksatoError,
    is_fatal_error,
    is_retryable_error,
)


def test_base_error():
    err = ZksatoError("test message")
    assert str(err) == "test message"
    assert err.message == "test message"
    assert err.details == {}


def test_error_with_details():
    err = ZksatoError("test", {"key": "value"})
    assert err.details == {"key": "value"}
    assert "details" in str(err)


def test_exception_hierarchy():
    # Configuration
    assert issubclass(ConfigurationError, ZksatoError)

    # Validation
    assert issubclass(ValidationError, ZksatoError)

    # Market data
    assert issubclass(MarketDataError, ZksatoError)
    assert issubclass(StaleMarketDataError, MarketDataError)
    assert issubclass(MarketClosedError, MarketDataError)

    # Broker
    assert issubclass(BrokerError, ZksatoError)
    assert issubclass(BrokerConnectionError, BrokerError)
    assert issubclass(BrokerAuthenticationError, BrokerError)

    # Order
    assert issubclass(OrderError, ZksatoError)
    assert issubclass(OrderRejectedError, OrderError)
    assert issubclass(OrderNotFoundError, OrderError)
    assert issubclass(OrderCancellationError, OrderError)

    # Risk
    assert issubclass(RiskError, ZksatoError)
    assert issubclass(RiskLimitExceededError, RiskError)
    assert issubclass(KillSwitchActiveError, RiskError)

    # Reconciliation
    assert issubclass(ReconciliationError, ZksatoError)
    assert issubclass(ReconciliationMismatchError, ReconciliationError)
    assert issubclass(ReconciliationRequiredError, ReconciliationError)

    # Strategy
    assert issubclass(StrategyError, ZksatoError)
    assert issubclass(StrategyNotFoundError, StrategyError)
    assert issubclass(BacktestError, StrategyError)

    # Auth
    assert issubclass(AuthenticationError, ZksatoError)
    assert issubclass(AuthorizationError, ZksatoError)

    # Session
    assert issubclass(SessionError, ZksatoError)
    assert issubclass(SessionExpiredError, SessionError)

    # Other
    assert issubclass(RateLimitError, ZksatoError)
    assert issubclass(IdempotencyError, ZksatoError)
    assert issubclass(PersistenceError, ZksatoError)
    assert issubclass(MigrationError, ZksatoError)
    assert issubclass(AgentError, ZksatoError)
    assert issubclass(AgentSubAccountError, AgentError)
    assert issubclass(AgentSkillError, AgentError)
    assert issubclass(NotificationError, ZksatoError)
    assert issubclass(PredictionMarketError, ZksatoError)
    assert issubclass(TFEXError, ZksatoError)
    assert issubclass(TFEXContractError, TFEXError)
    assert issubclass(TFEXMarginError, TFEXError)


def test_is_retryable_error():
    assert is_retryable_error(BrokerConnectionError("test")) is True
    assert is_retryable_error(BrokerError("test")) is True
    assert is_retryable_error(PersistenceError("test")) is True
    assert is_retryable_error(RateLimitError("test")) is True
    assert is_retryable_error(ReconciliationError("test")) is True

    assert is_retryable_error(ConfigurationError("test")) is False
    assert is_retryable_error(ValidationError("test")) is False
    assert is_retryable_error(OrderRejectedError("test")) is False


def test_is_fatal_error():
    assert is_fatal_error(ConfigurationError("test")) is True
    assert is_fatal_error(ValidationError("test")) is True
    assert is_fatal_error(AuthenticationError("test")) is True
    assert is_fatal_error(AuthorizationError("test")) is True
    assert is_fatal_error(KillSwitchActiveError("test")) is True
    assert is_fatal_error(OrderRejectedError("test")) is True
    assert is_fatal_error(RiskLimitExceededError("test")) is True

    assert is_fatal_error(BrokerConnectionError("test")) is False
    assert is_fatal_error(PersistenceError("test")) is False
