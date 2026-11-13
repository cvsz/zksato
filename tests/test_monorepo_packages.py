"""Tests for monorepo package imports."""


def test_all_packages_importable():
    """Test that all 10 packages and 3 apps are importable."""
    import zksato_core
    import zksato_market
    import zksato_risk

    assert zksato_core.__version__ == "2.0.0-dev"
    assert zksato_risk.__version__ == "2.0.0-dev"
    assert zksato_market.__version__ == "2.0.0-dev"


def test_core_exports():
    """Test core package exports key types."""
    from zksato_core.config import Settings
    from zksato_core.datetime import BANGKOK_TZ, now_bangkok
    from zksato_core.ids import new_idempotency_key, new_ulid
    from zksato_core.money import thb
    from zksato_core.observability import setup_observability
    from zksato_core.serialization import generate_idempotency_key, stable_json_dumps
    from zksato_core.telemetry import TelemetryLogger, TradingEvent, TradingEventType
    from zksato_core.types import OrderType, Side, TradingMode

    assert Side.BUY
    assert OrderType.LIMIT
    assert TradingMode.PAPER
    assert new_ulid()
    assert new_idempotency_key()
    assert thb(100)
    assert BANGKOK_TZ
    assert now_bangkok()
    assert stable_json_dumps({"a": 1}) == '{"a":1}'
    assert generate_idempotency_key({"symbol": "TEST", "side": "BUY", "quantity": 100})
    assert callable(setup_observability)
    assert TradingEvent
    assert TradingEventType
    assert TelemetryLogger
    assert Settings


def test_risk_exports():
    """Test risk package exports key types."""
    from zksato_risk.checks.market import QuoteStalenessCheck
    from zksato_risk.checks.notional import NotionalLimitCheck
    from zksato_risk.checks.position import PositionLimitCheck
    from zksato_risk.engine import RiskEngine
    from zksato_risk.policies.approval import ConfirmationBus, FourEyesPolicy
    from zksato_risk.policies.base import Policy, PolicyEngine, PolicyRegistry
    from zksato_risk.policies.loader import PolicyLoader
    from zksato_risk.policies.registry import create_policy_engine, get_registry
    from zksato_risk.policies.trading import create_default_policies

    assert RiskEngine
    assert Policy
    assert PolicyEngine
    assert PolicyRegistry
    assert get_registry
    assert create_policy_engine
    assert PolicyLoader
    assert create_default_policies
    assert ConfirmationBus
    assert FourEyesPolicy
    assert PositionLimitCheck
    assert NotionalLimitCheck
    assert QuoteStalenessCheck


def test_market_exports():
    """Test market package exports key types."""
    from zksato_market.adapters import MarketDataAdapter
    from zksato_market.calendar import TradingCalendar
    from zksato_market.feeds import CompositeFeed, Feed, MarketDataFeed
    from zksato_market.feeds.ccxt import CCXTFeed
    from zksato_market.feeds.composite import FeedRouter
    from zksato_market.feeds.settrade import SettradeFeed
    from zksato_market.reference import ReferenceData
    from zksato_market.scanner import MarketScanner
    from zksato_market.types import MarketType, Quote, Trade

    assert MarketType
    assert Quote
    assert Trade
    assert Feed
    assert MarketDataFeed
    assert CompositeFeed
    assert SettradeFeed
    assert CCXTFeed
    assert FeedRouter
    assert MarketDataAdapter
    assert MarketScanner
    assert TradingCalendar
    assert ReferenceData


def test_broker_exports():
    """Test broker package exports key types."""
    from zksato_broker import BrokerAdapter, BrokerCapabilities
    from zksato_broker.ccxt import CCXTBroker
    from zksato_broker.errors import BrokerError, BrokerErrorCategory
    from zksato_broker.paper import PaperBroker
    from zksato_broker.router import BrokerRouter
    from zksato_broker.sandbox import SandboxManager
    from zksato_broker.settrade import SettradeBroker

    assert BrokerAdapter
    assert BrokerCapabilities
    assert PaperBroker
    assert SettradeBroker
    assert CCXTBroker
    assert BrokerError
    assert BrokerErrorCategory
    assert BrokerRouter
    assert SandboxManager


def test_strategy_exports():
    """Test strategy package exports key types."""
    from zksato_strategy.backtest import BacktestEngine
    from zksato_strategy.hyperopt import HyperoptEngine
    from zksato_strategy.indicators import ema, rsi, sma_series
    from zksato_strategy.pairlist import PairListManager
    from zksato_strategy.registry import PluginRegistry
    from zksato_strategy.research import ResearchEngine
    from zksato_strategy.research.memory import StrategyMemory
    from zksato_strategy.strategies.classic import StrategyEngine
    from zksato_strategy.trailing_stop import TrailingStop

    assert StrategyEngine
    assert rsi
    assert ema
    assert sma_series
    assert BacktestEngine
    assert HyperoptEngine
    assert PairListManager
    assert TrailingStop
    assert ResearchEngine
    assert PluginRegistry
    assert StrategyMemory


def test_portfolio_exports():
    """Test portfolio package exports key types."""
    from zksato_portfolio.outbox import OutboxDelivery
    from zksato_portfolio.persistence import PersistenceLayer
    from zksato_portfolio.portfolio import PortfolioManager
    from zksato_portfolio.reconcile import ReconciliationEngine
    from zksato_portfolio.session_reconcile import SessionReconciliation
    from zksato_portfolio.store import StateStore

    assert PortfolioManager
    assert ReconciliationEngine
    assert SessionReconciliation
    assert PersistenceLayer
    assert StateStore
    assert OutboxDelivery


def test_automation_exports():
    """Test automation package exports key types."""
    from zksato_automation.agent_os.a2a import A2AMessage, AgentRegistry
    from zksato_automation.agent_os.engine import AgentEngine
    from zksato_automation.agent_os.session import AgentSession
    from zksato_automation.agent_os.skills import SkillRegistry
    from zksato_automation.agent_os.subaccount import SubAccount
    from zksato_automation.scheduler import TradingScheduler
    from zksato_automation.scheduler.hooks import HookManager
    from zksato_automation.scheduler.state import CheckpointManager
    from zksato_automation.service import TradingService
    from zksato_automation.tools.registry import ToolRegistry

    assert TradingScheduler
    assert TradingService
    assert SkillRegistry
    assert SubAccount
    assert AgentEngine
    assert AgentSession
    assert ToolRegistry
    assert HookManager
    assert AgentRegistry
    assert A2AMessage
    assert CheckpointManager


def test_api_exports():
    """Test API package exports key types."""
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

    assert app
    assert AuthManager
    assert SecurityManager
    assert ApprovalManager
    assert CoordinationService
    assert DashboardService
    assert MarketTerminal
    assert TradingViewWebhook
    assert NotificationManager
    assert ProductionManager
    assert OpenAPIContract
    assert LLMClientFactory
    assert PredictionMarketManager
    assert TFEXManager


def test_cli_exports():
    """Test CLI package exports key types."""
    from zksato_cli.commands import agent, bot, broker, config, portfolio, risk, strategy
    from zksato_cli.main import app as cli_app

    assert cli_app
    assert bot
    assert strategy
    assert risk
    assert broker
    assert portfolio
    assert agent
    assert config


def test_test_utils_exports():
    """Test test-utils package exports key types."""
    from zksato_test_utils.assertions import assert_order_filled, assert_risk_rejected
    from zksato_test_utils.fixtures import mock_broker, mock_market_feed
    from zksato_test_utils.generators import generate_fills, generate_orders

    assert mock_broker
    assert mock_market_feed
    assert generate_orders
    assert generate_fills
    assert assert_order_filled
    assert assert_risk_rejected
