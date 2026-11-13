"""zksato-risk: Risk engine, policies, and checks for zksato trading platform."""

from zksato_risk.checks.base import BaseRiskCheck, CompositeRiskCheck, RiskCheck
from zksato_risk.checks.market import (
    AccountAllowListCheck,
    KillSwitchCheck,
    MarketDataAvailabilityCheck,
    MarketSessionCheck,
    OpenOrderCheck,
    OrderCountCheck,
    PriceBandCheck,
    QuoteStalenessCheck,
    SpreadCheck,
    TickSizeCheck,
)
from zksato_risk.checks.notional import (
    DailyLossLimitCheck,
    DrawdownLimitCheck,
    GrossExposureCheck,
    LineAvailabilityCheck,
    NetExposureCheck,
    NotionalLimitCheck,
    PerTradeRiskCheck,
    PriceDeviationCheck,
    StopLossCheck,
    TakeProfitCheck,
)
from zksato_risk.checks.portfolio import (
    AllocationCheck,
    CorrelationCheck,
    CVaRCheck,
    PortfolioRiskManager,
    StrategyConflictCheck,
    VaRCheck,
)
from zksato_risk.checks.position import (
    BoardLotCheck,
    ConcentrationCheck,
    PositionLimitCheck,
    PositionSizeCheck,
    ShortSellingCheck,
)
from zksato_risk.engine import RiskEngine
from zksato_risk.metrics import RiskEngineMetrics, RiskEvaluationMetrics
from zksato_risk.policies.approval import (
    ApprovalManager,
    ApprovalMode,
    ApprovalRequest,
    ApprovalStatus,
    ConfirmationBus,
    FourEyesPolicy,
)
from zksato_risk.policies.base import (
    Policy,
    PolicyDecision,
    PolicyEngine,
    PolicyRegistry,
    PolicyResult,
)
from zksato_risk.policies.loader import PolicyConfig, PolicyFile, PolicyLoader
from zksato_risk.policies.registry import (
    create_policy_engine,
    discover_policies,
    get_registry,
    register_policy,
)
from zksato_risk.policies.trading import (
    AccountAllowListPolicy,
    BoardLotPolicy,
    ExposureLimitPolicy,
    KillSwitchPolicy,
    LineAvailabilityPolicy,
    MarketDataAvailabilityPolicy,
    MarketSessionPolicy,
    NotionalLimitPolicy,
    OpenOrderLimitPolicy,
    OrderCountLimitPolicy,
    PerTradeRiskPolicy,
    PriceBandPolicy,
    PriceDeviationPolicy,
    ShortSellingPolicy,
    StopLossPolicy,
    TakeProfitPolicy,
    TickSizePolicy,
    create_default_policies,
)

__version__ = "2.0.0-dev"

__all__ = [
    # Engine
    "RiskEngine",
    # Policies base
    "Policy",
    "PolicyDecision",
    "PolicyResult",
    "PolicyEngine",
    "PolicyRegistry",
    # Policies registry
    "get_registry",
    "register_policy",
    "create_policy_engine",
    "discover_policies",
    # Policies loader
    "PolicyLoader",
    "PolicyConfig",
    "PolicyFile",
    # Trading policies
    "KillSwitchPolicy",
    "AccountAllowListPolicy",
    "MarketDataAvailabilityPolicy",
    "MarketSessionPolicy",
    "PriceBandPolicy",
    "TickSizePolicy",
    "ShortSellingPolicy",
    "BoardLotPolicy",
    "OrderCountLimitPolicy",
    "OpenOrderLimitPolicy",
    "ExposureLimitPolicy",
    "NotionalLimitPolicy",
    "StopLossPolicy",
    "TakeProfitPolicy",
    "LineAvailabilityPolicy",
    "PriceDeviationPolicy",
    "PerTradeRiskPolicy",
    "create_default_policies",
    # Approval policies
    "ApprovalMode",
    "ApprovalStatus",
    "ApprovalRequest",
    "FourEyesPolicy",
    "ApprovalManager",
    "ConfirmationBus",
    # Checks base
    "RiskCheck",
    "BaseRiskCheck",
    "CompositeRiskCheck",
    # Position checks
    "PositionLimitCheck",
    "PositionSizeCheck",
    "ConcentrationCheck",
    "ShortSellingCheck",
    "BoardLotCheck",
    # Notional checks
    "NotionalLimitCheck",
    "DailyLossLimitCheck",
    "DrawdownLimitCheck",
    "GrossExposureCheck",
    "NetExposureCheck",
    "LineAvailabilityCheck",
    "PerTradeRiskCheck",
    "StopLossCheck",
    "TakeProfitCheck",
    "PriceDeviationCheck",
    # Market checks
    "MarketDataAvailabilityCheck",
    "MarketSessionCheck",
    "QuoteStalenessCheck",
    "SpreadCheck",
    "PriceBandCheck",
    "TickSizeCheck",
    "OrderCountCheck",
    "OpenOrderCheck",
    "AccountAllowListCheck",
    "KillSwitchCheck",
    # Portfolio checks
    "VaRCheck",
    "CVaRCheck",
    "CorrelationCheck",
    "AllocationCheck",
    "StrategyConflictCheck",
    "PortfolioRiskManager",
    # Metrics
    "RiskEvaluationMetrics",
    "RiskEngineMetrics",
]
