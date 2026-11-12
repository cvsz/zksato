"""zksato-broker: Broker adapters, routing, and sandbox management for zksato trading platform."""

from zksato_broker.protocol import BrokerAdapter, BrokerCapabilities
from zksato_broker.base import BaseBroker
from zksato_broker.paper import PaperBroker
from zksato_broker.settrade import SettradeBroker
from zksato_broker.ccxt import CCXTBroker
from zksato_broker.prediction import PredictionBroker
from zksato_broker.errors import (
    BrokerError,
    BrokerErrorCategory,
    BrokerConnectionError,
    BrokerAuthenticationError,
    BrokerRateLimitError,
    BrokerInvalidOrderError,
    BrokerRejectedError,
    BrokerUnknownError,
    classify_error,
    RETRY_POLICIES,
    RetryPolicy,
)
from zksato_broker.router import BrokerRouter
from zksato_broker.sandbox import SandboxManager, SandboxConfig, SandboxRuntime

__version__ = "2.0.0-dev"

__all__ = [
    # Protocol
    "BrokerAdapter",
    "BrokerCapabilities",
    # Base
    "BaseBroker",
    # Implementations
    "PaperBroker",
    "SettradeBroker",
    "CCXTBroker",
    "PredictionBroker",
    # Errors
    "BrokerError",
    "BrokerErrorCategory",
    "BrokerConnectionError",
    "BrokerAuthenticationError",
    "BrokerRateLimitError",
    "BrokerInvalidOrderError",
    "BrokerRejectedError",
    "BrokerUnknownError",
    "classify_error",
    "RETRY_POLICIES",
    "RetryPolicy",
    # Router
    "BrokerRouter",
    # Sandbox
    "SandboxManager",
    "SandboxConfig",
    "SandboxRuntime",
]