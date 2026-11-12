"""TOML/YAML policy loader with validation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from zksato_core.config import BaseConfig
from zksato_core.models import OrderIntent, RiskContext, Side
from zksato_risk.policies.base import Policy, PolicyDecision, PolicyResult


class PolicyConfig(BaseModel):
    """Configuration for a single policy."""

    name: str
    type: str
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    decision: str = "reject"  # reject, warn, require_approval
    applies_to: list[str] = Field(default_factory=list)  # symbols, strategies, etc.


class PolicyFile(BaseModel):
    """Policy file structure."""

    version: str = "1.0"
    policies: list[PolicyConfig] = Field(default_factory=list)


class PolicyLoader:
    """Load policies from TOML/YAML files."""

    def __init__(self, config: BaseConfig) -> None:
        self.config = config

    def load_toml(self, path: Path) -> PolicyFile:
        """Load policies from TOML file."""
        with path.open("rb") as f:
            data = tomllib.load(f)
        return PolicyFile(**data)

    def load_yaml(self, path: Path) -> PolicyFile:
        """Load policies from YAML file."""
        with path.open("r") as f:
            data = yaml.safe_load(f)
        return PolicyFile(**data)

    def load(self, path: Path) -> PolicyFile:
        """Load policies from file (auto-detect format)."""
        if path.suffix in {".toml"}:
            return self.load_toml(path)
        elif path.suffix in {".yaml", ".yml"}:
            return self.load_yaml(path)
        else:
            raise ValueError(f"Unsupported policy file format: {path.suffix}")

    def create_policies(self, policy_file: PolicyFile) -> list[Policy]:
        """Create policy instances from config."""
        policies = []

        for policy_config in policy_file.policies:
            if not policy_config.enabled:
                continue

            policy = self._create_policy(policy_config)
            if policy:
                policies.append(policy)

        return policies

    def _create_policy(self, config: PolicyConfig) -> Policy | None:
        """Create a policy instance from config."""
        policy_type = config.type.lower()

        if policy_type == "notional_limit":
            return NotionalLimitPolicy(config.parameters)
        elif policy_type == "position_limit":
            return PositionLimitPolicy(config.parameters)
        elif policy_type == "daily_loss_limit":
            return DailyLossLimitPolicy(config.parameters)
        elif policy_type == "drawdown_limit":
            return DrawdownLimitPolicy(config.parameters)
        elif policy_type == "concentration_limit":
            return ConcentrationLimitPolicy(config.parameters)
        elif policy_type == "spread_limit":
            return SpreadLimitPolicy(config.parameters)
        elif policy_type == "staleness_limit":
            return StalenessLimitPolicy(config.parameters)
        elif policy_type == "stop_loss_required":
            return StopLossRequiredPolicy(config.parameters)
        else:
            return None


class NotionalLimitPolicy(Policy):
    """Policy to limit order notional value."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_notional = params.get("max_notional", 100_000)

    @property
    def name(self) -> str:
        return "notional_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.reference_price:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["reference price required for notional check"],
            )

        notional = float(context.reference_price * intent.quantity)
        if notional > self._max_notional:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[f"order notional {notional:.2f} exceeds limit {self._max_notional:.2f}"],
            )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class PositionLimitPolicy(Policy):
    """Policy to limit number of positions."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_positions = params.get("max_positions", 5)

    @property
    def name(self) -> str:
        return "position_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if intent.side == Side.BUY and context.opens_new_position:
            if context.current_positions >= self._max_positions:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=[f"maximum positions ({self._max_positions}) reached"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class DailyLossLimitPolicy(Policy):
    """Policy to limit daily loss."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_daily_loss_pct = params.get("max_daily_loss_pct", 2.0)

    @property
    def name(self) -> str:
        return "daily_loss_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if intent.side == Side.BUY and not context.reduces_exposure:
            if context.daily_pnl_pct <= -self._max_daily_loss_pct:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=[f"daily loss limit ({self._max_daily_loss_pct}%) reached"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class DrawdownLimitPolicy(Policy):
    """Policy to limit drawdown."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_drawdown_pct = params.get("max_drawdown_pct", 5.0)

    @property
    def name(self) -> str:
        return "drawdown_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if intent.side == Side.BUY and not context.reduces_exposure:
            if context.drawdown_pct >= self._max_drawdown_pct:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=[f"drawdown limit ({self._max_drawdown_pct}%) reached"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class ConcentrationLimitPolicy(Policy):
    """Policy to limit symbol/sector concentration."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_symbol_pct = params.get("max_symbol_pct", 20.0)
        self._max_sector_pct = params.get("max_sector_pct", 35.0)

    @property
    def name(self) -> str:
        return "concentration_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        reasons: list[str] = []

        if context.symbol_exposure_pct > self._max_symbol_pct:
            reasons.append(
                f"symbol exposure {context.symbol_exposure_pct:.1f}% exceeds limit {self._max_symbol_pct:.1f}%"
            )

        if context.sector_exposure_pct > self._max_sector_pct:
            reasons.append(
                f"sector exposure {context.sector_exposure_pct:.1f}% exceeds limit {self._max_sector_pct:.1f}%"
            )

        if reasons:
            return PolicyResult(decision=PolicyDecision.REJECT, reasons=reasons)

        return PolicyResult(decision=PolicyDecision.APPROVE)


class SpreadLimitPolicy(Policy):
    """Policy to limit bid/ask spread."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_spread_pct = params.get("max_spread_pct", 3.0)

    @property
    def name(self) -> str:
        return "spread_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if context.spread_pct is not None and context.spread_pct > self._max_spread_pct:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[
                    f"spread {context.spread_pct:.2f}% exceeds limit {self._max_spread_pct:.2f}%"
                ],
            )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class StalenessLimitPolicy(Policy):
    """Policy to limit quote staleness."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._max_age_seconds = params.get("max_age_seconds", 10.0)

    @property
    def name(self) -> str:
        return "staleness_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if (
            context.quote_age_seconds is not None
            and context.quote_age_seconds > self._max_age_seconds
        ):
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[
                    f"quote age {context.quote_age_seconds:.1f}s exceeds limit {self._max_age_seconds:.1f}s"
                ],
            )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class StopLossRequiredPolicy(Policy):
    """Policy to require stop loss on buy orders."""

    def __init__(self, params: dict[str, Any]) -> None:
        self._params = params
        self._required = params.get("required", True)

    @property
    def name(self) -> str:
        return "stop_loss_required"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if self._required and intent.side == Side.BUY and not context.reduces_exposure:
            if intent.stop_loss is None:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=["stop loss is required for buy orders"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)
