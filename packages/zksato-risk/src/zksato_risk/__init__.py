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
    "AccountAllowListCheck",
    "AccountAllowListPolicy",
    "AllocationCheck",
    "ApprovalManager",
    # Approval policies
    "ApprovalMode",
    "ApprovalRequest",
    "ApprovalStatus",
    "BaseRiskCheck",
    "BoardLotCheck",
    "BoardLotPolicy",
    "CVaRCheck",
    "CompositeRiskCheck",
    "ConcentrationCheck",
    "ConfirmationBus",
    "CorrelationCheck",
    "DailyLossLimitCheck",
    "DrawdownLimitCheck",
    "ExposureLimitPolicy",
    "FourEyesPolicy",
    "GrossExposureCheck",
    "KillSwitchCheck",
    # Trading policies
    "KillSwitchPolicy",
    "LineAvailabilityCheck",
    "LineAvailabilityPolicy",
    # Market checks
    "MarketDataAvailabilityCheck",
    "MarketDataAvailabilityPolicy",
    "MarketSessionCheck",
    "MarketSessionPolicy",
    "NetExposureCheck",
    # Notional checks
    "NotionalLimitCheck",
    "NotionalLimitPolicy",
    "OpenOrderCheck",
    "OpenOrderLimitPolicy",
    "OrderCountCheck",
    "OrderCountLimitPolicy",
    "PerTradeRiskCheck",
    "PerTradeRiskPolicy",
    # Policies base
    "Policy",
    "PolicyConfig",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyFile",
    # Policies loader
    "PolicyLoader",
    "PolicyRegistry",
    "PolicyResult",
    "PortfolioRiskManager",
    # Position checks
    "PositionLimitCheck",
    "PositionSizeCheck",
    "PriceBandCheck",
    "PriceBandPolicy",
    "PriceDeviationCheck",
    "PriceDeviationPolicy",
    "QuoteStalenessCheck",
    # Checks base
    "RiskCheck",
    # Engine
    "RiskEngine",
    "RiskEngineMetrics",
    # Metrics
    "RiskEvaluationMetrics",
    "ShortSellingCheck",
    "ShortSellingPolicy",
    "SpreadCheck",
    "StopLossCheck",
    "StopLossPolicy",
    "StrategyConflictCheck",
    "TakeProfitCheck",
    "TakeProfitPolicy",
    "TickSizeCheck",
    "TickSizePolicy",
    # Portfolio checks
    "VaRCheck",
    "create_default_policies",
    "create_policy_engine",
    "discover_policies",
    # Policies registry
    "get_registry",
    "register_policy",
]
