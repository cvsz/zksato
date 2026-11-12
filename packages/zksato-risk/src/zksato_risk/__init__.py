"""zksato-risk: Risk engine, policies, and checks for zksato trading platform."""

from zksato_risk.engine import RiskEngine
from zksato_risk.policies.base import Policy, PolicyDecision, PolicyResult, PolicyEngine, PolicyRegistry
from zksato_risk.policies.registry import get_registry, register_policy, create_policy_engine, discover_policies
from zksato_risk.policies.loader import PolicyLoader, PolicyConfig, PolicyFile
from zksato_risk.policies.trading import (
    KillSwitchPolicy,
    AccountAllowListPolicy,
    MarketDataAvailabilityPolicy,
    MarketSessionPolicy,
    PriceBandPolicy,
    TickSizePolicy,
    ShortSellingPolicy,
    BoardLotPolicy,
    OrderCountLimitPolicy,
    OpenOrderLimitPolicy,
    ExposureLimitPolicy,
    NotionalLimitPolicy,
    StopLossPolicy,
    TakeProfitPolicy,
    LineAvailabilityPolicy,
    PriceDeviationPolicy,
    PerTradeRiskPolicy,
    create_default_policies,
)
from zksato_risk.policies.approval import (
    ApprovalMode,
    ApprovalStatus,
    ApprovalRequest,
    FourEyesPolicy,
    ApprovalManager,
    ConfirmationBus,
)
from zksato_risk.checks.base import RiskCheck, BaseRiskCheck, CompositeRiskCheck
from zksato_risk.checks.position import (
    PositionLimitCheck,
    PositionSizeCheck,
    ConcentrationCheck,
    ShortSellingCheck,
    BoardLotCheck,
)
from zksato_risk.checks.notional import (
    NotionalLimitCheck,
    DailyLossLimitCheck,
    DrawdownLimitCheck,
    GrossExposureCheck,
    NetExposureCheck,
    LineAvailabilityCheck,
    PerTradeRiskCheck,
    StopLossCheck,
    TakeProfitCheck,
    PriceDeviationCheck,
)
from zksato_risk.checks.market import (
    MarketDataAvailabilityCheck,
    MarketSessionCheck,
    QuoteStalenessCheck,
    SpreadCheck,
    PriceBandCheck,
    TickSizeCheck,
    OrderCountCheck,
    OpenOrderCheck,
    AccountAllowListCheck,
    KillSwitchCheck,
)
from zksato_risk.checks.portfolio import (
    VaRCheck,
    CVaRCheck,
    CorrelationCheck,
    AllocationCheck,
    StrategyConflictCheck,
    PortfolioRiskManager,
)
from zksato_risk.metrics import RiskEvaluationMetrics, RiskEngineMetrics

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