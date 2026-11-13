"""zksato-api: FastAPI REST API and dashboard for zksato."""

from zksato_api.approvals import ApprovalManager
from zksato_api.auth import AuthManager
from zksato_api.coordination import CoordinationService
from zksato_api.dashboard import DashboardService
from zksato_api.llm_clients import LLMClientFactory
from zksato_api.main import app
from zksato_api.market_terminal import MarketTerminal
from zksato_api.notifications import NotificationManager
from zksato_api.openapi_contract import OpenAPIContract
from zksato_api.prediction import PredictionMarketManager
from zksato_api.production import ProductionManager
from zksato_api.security import SecurityManager
from zksato_api.tfex import TFEXManager
from zksato_api.tradingview import TradingViewWebhook

__version__ = "2.0.0-dev"

__all__ = [
    "ApprovalManager",
    "AuthManager",
    "CoordinationService",
    "DashboardService",
    "LLMClientFactory",
    "MarketTerminal",
    "NotificationManager",
    "OpenAPIContract",
    "PredictionMarketManager",
    "ProductionManager",
    "SecurityManager",
    "TFEXManager",
    "TradingViewWebhook",
    "app",
]
