"""Portfolio risk checks: VaR, CVaR, correlation."""

from __future__ import annotations

from zksato_core.models import OrderIntent, RiskContext
from zksato_risk.checks.base import BaseRiskCheck


class VaRCheck(BaseRiskCheck):
    """Value-at-Risk check."""

    def __init__(
        self,
        confidence_level: float = 0.95,
        portfolio_value: float = 100_000.0,
        max_var_pct: float = 5.0,
    ) -> None:
        self.confidence_level = confidence_level
        self.portfolio_value = portfolio_value
        self.max_var_pct = max_var_pct
        self.name = "var"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        # Conservative VaR proxy: current drawdown as worst-case loss at confidence level.
        # Historical-return VaR is computed via PortfolioRiskManager.calculate_var when a
        # returns series is supplied externally; here we fail closed on drawdown.
        if context.drawdown_pct > self.max_var_pct:
            reasons.append(
                f"VaR estimate {context.drawdown_pct:.2f}% exceeds max {self.max_var_pct:.2f}%"
            )
        return reasons


class CVaRCheck(BaseRiskCheck):
    """Conditional Value-at-Risk check."""

    def __init__(
        self,
        confidence_level: float = 0.95,
        portfolio_value: float = 100_000.0,
        max_cvar_pct: float = 7.0,
    ) -> None:
        self.confidence_level = confidence_level
        self.portfolio_value = portfolio_value
        self.max_cvar_pct = max_cvar_pct
        self.name = "cvar"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        # CVaR proxy: negative daily PnL as expected tail loss beyond VaR.
        cvar_estimate = abs(context.daily_pnl_pct) if context.daily_pnl_pct < 0 else 0.0
        if cvar_estimate > self.max_cvar_pct:
            reasons.append(
                f"CVaR estimate {cvar_estimate:.2f}% exceeds max {self.max_cvar_pct:.2f}%"
            )
        return reasons


class CorrelationCheck(BaseRiskCheck):
    """Correlation/concentration proxy check."""

    def __init__(self, max_correlation: float = 0.7) -> None:
        self.max_correlation = max_correlation
        self.name = "correlation"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        # Sector exposure as correlation/concentration proxy.
        if context.sector_exposure_pct > self.max_correlation * 100.0:
            reasons.append(
                f"sector exposure {context.sector_exposure_pct:.2f}% exceeds correlation proxy "
                f"{self.max_correlation:.2f}"
            )
        return reasons


class AllocationCheck(BaseRiskCheck):
    """Allocation limit check."""

    def __init__(self, max_allocation_pct: float = 20.0) -> None:
        self.max_allocation_pct = max_allocation_pct
        self.name = "allocation"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        # Projected position allocation after the trade.
        if context.position_pct_after_trade > self.max_allocation_pct:
            reasons.append(
                f"position allocation {context.position_pct_after_trade:.2f}% exceeds max "
                f"{self.max_allocation_pct:.2f}%"
            )
        return reasons


class StrategyConflictCheck(BaseRiskCheck):
    """Check for conflicting strategies."""

    def __init__(self, conflicting_strategies: str = "") -> None:
        self.conflicting_strategies = conflicting_strategies
        self.name = "strategy_conflict"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        if not self.conflicting_strategies:
            return reasons
        conflicts = {
            pair.strip() for pair in self.conflicting_strategies.split(",") if pair.strip()
        }
        intent_source = intent.source.strip()
        for conflict in conflicts:
            parts = conflict.split("-")
            if len(parts) != 2:
                continue
            a, b = parts[0].strip(), parts[1].strip()
            if intent_source == a:
                reasons.append(f"strategy {intent_source} conflicts with active {b}")
            elif intent_source == b:
                reasons.append(f"strategy {intent_source} conflicts with active {a}")
        return reasons


class PortfolioRiskManager:
    """Manages portfolio-level risk checks."""

    def __init__(
        self,
        max_correlation: float = 0.7,
        max_allocation_pct: float = 20.0,
        conflicting_strategies: str = "",
    ) -> None:
        self.max_correlation = max_correlation
        self.max_allocation_pct = max_allocation_pct
        self.conflicting_strategies = conflicting_strategies

    def check_concentration(self, symbol: str, portfolio_positions: list[str]) -> list[str]:
        """Warn if adding a symbol would exceed concentration threshold."""
        reasons: list[str] = []
        total = len(portfolio_positions) + 1
        same_count = sum(1 for s in portfolio_positions if s == symbol)
        if total > 0 and (same_count + 1) / total > self.max_correlation:
            reasons.append(
                f"symbol {symbol} concentration proxy exceeds max {self.max_correlation:.2f}"
            )
        return reasons

    def check_allocation(
        self, symbol: str, portfolio_positions: list[str], max_allocation_pct: float
    ) -> list[str]:
        """Warn if a single symbol exceeds allocation limit."""
        reasons: list[str] = []
        total = len(portfolio_positions) + 1
        if total > 0 and (1.0 / total) * 100 > max_allocation_pct:
            reasons.append(f"symbol {symbol} allocation exceeds {max_allocation_pct:.1f}%")
        return reasons

    def check_conflict(self, strategy: str, active_strategies: list[str]) -> list[str]:
        """Warn if a conflicting strategy is already active on the same symbol."""
        reasons: list[str] = []
        if not self.conflicting_strategies:
            return reasons
        conflicts = {
            pair.strip() for pair in self.conflicting_strategies.split(",") if pair.strip()
        }
        for conflict in conflicts:
            parts = conflict.split("-")
            if len(parts) != 2:
                continue
            a, b = parts[0].strip(), parts[1].strip()
            if strategy == a and b in active_strategies:
                reasons.append(f"strategy {strategy} conflicts with active {b}")
            if strategy == b and a in active_strategies:
                reasons.append(f"strategy {strategy} conflicts with active {a}")
        return reasons

    def calculate_var(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        portfolio_value: float = 100_000.0,
    ) -> float:
        """Computes Historical Value-at-Risk (VaR) in USD using linear interpolation."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        n = len(sorted_returns)
        rank = (1.0 - confidence_level) * (n - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = rank - lower_idx
        loss_pct = abs(
            min(
                0.0,
                sorted_returns[lower_idx]
                + fraction * (sorted_returns[upper_idx] - sorted_returns[lower_idx]),
            )
        )
        return loss_pct * portfolio_value

    def calculate_expected_shortfall(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        portfolio_value: float = 100_000.0,
    ) -> float:
        """Computes Conditional Value-at-Risk (CVaR / Expected Shortfall) in USD."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        idx = max(1, int((1.0 - confidence_level) * len(sorted_returns)))
        tail_losses = [abs(min(0.0, r)) for r in sorted_returns[:idx]]
        avg_tail_loss = sum(tail_losses) / len(tail_losses) if tail_losses else 0.0
        return avg_tail_loss * portfolio_value

    def evaluate(
        self,
        symbol: str,
        strategy: str,
        portfolio_positions: list[str],
        active_strategies: list[str],
    ) -> list[str]:
        """Run all portfolio checks and return combined reasons."""
        reasons: list[str] = []
        reasons.extend(self.check_concentration(symbol, portfolio_positions))
        reasons.extend(self.check_allocation(symbol, portfolio_positions, self.max_allocation_pct))
        reasons.extend(self.check_conflict(strategy, active_strategies))
        return reasons
