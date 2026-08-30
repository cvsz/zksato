from __future__ import annotations

from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, RiskDecision, Side


class RiskEngine:
    """Deterministic pre-trade checks that automation and AI cannot bypass."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> RiskDecision:
        reasons: list[str] = []
        price = intent.price or context.reference_price or 0.0
        estimated_notional = price * intent.quantity if price > 0 else 0.0
        estimated_risk_pct: float | None = None
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure
        is_prediction = intent.side in {Side.UP, Side.DOWN}

        if self.settings.kill_switch:
            reasons.append("global kill switch is active")
        if not context.account_allowed:
            reasons.append("account is not in the configured trading allow-list")
        if not context.market_data_available:
            reasons.append("trusted market data is unavailable")
        if not context.market_session_known:
            reasons.append("market session state is unknown")
        elif opening_risk and not context.market_session_open:
            reasons.append("market session is closed for new exposure")
        if not context.price_band_ok:
            reasons.append("order price is outside the trusted price band")
        if not context.tick_size_ok:
            reasons.append("order price is not aligned to the trusted tick size")
        if not is_prediction:
            if (
                intent.side == Side.SELL
                and not context.reduces_exposure
                and not self.settings.allow_equity_short_selling
            ):
                reasons.append("equity short selling is disabled")
            if (
                intent.side == Side.SELL
                and not self.settings.allow_equity_short_selling
                and context.available_quantity is not None
                and intent.quantity > context.available_quantity
            ):
                reasons.append("sell quantity exceeds available position")
            if opening_risk and context.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
                reasons.append("maximum daily loss threshold reached")
            if opening_risk and context.drawdown_pct >= self.settings.max_drawdown_pct:
                reasons.append("maximum drawdown threshold reached")
            if (
                opening_risk
                and context.opens_new_position
                and context.current_positions >= self.settings.max_positions
            ):
                reasons.append("maximum number of positions reached")
            if opening_risk and context.position_pct_after_trade > self.settings.max_position_pct:
                reasons.append("position size exceeds maximum portfolio percentage")
            if context.orders_today >= self.settings.max_orders_per_day:
                reasons.append("maximum daily order count reached")
            if context.open_orders >= self.settings.max_open_orders:
                reasons.append("maximum open order count reached")
            if opening_risk and context.gross_exposure_pct > self.settings.max_gross_exposure_pct:
                reasons.append("gross exposure exceeds configured maximum")
            if opening_risk and abs(context.net_exposure_pct) > self.settings.max_net_exposure_pct:
                reasons.append("net exposure exceeds configured maximum")
            if opening_risk and context.symbol_exposure_pct > self.settings.max_symbol_exposure_pct:
                reasons.append("symbol exposure exceeds configured maximum")
            if opening_risk and context.sector_exposure_pct > self.settings.max_sector_exposure_pct:
                reasons.append("sector exposure exceeds configured maximum")
            if (
                context.quote_age_seconds is not None
                and context.quote_age_seconds > self.settings.market_data_stale_seconds
            ):
                reasons.append("market quote is stale")
            if context.spread_pct is not None and context.spread_pct > self.settings.max_spread_pct:
                reasons.append("bid/offer spread exceeds configured maximum")
            if estimated_notional <= 0:
                reasons.append("reference price is required for risk estimation")
            elif estimated_notional > self.settings.max_notional_per_order:
                reasons.append("order notional exceeds configured maximum")
            if self.settings.require_stop_loss and opening_risk and intent.stop_loss is None:
                reasons.append("stop loss is required for buy orders")
            if (
                opening_risk
                and intent.stop_loss is not None
                and price > 0
                and intent.stop_loss >= price
            ):
                reasons.append("buy stop loss must be below entry price")
            if (
                opening_risk
                and intent.take_profit is not None
                and price > 0
                and intent.take_profit <= price
            ):
                reasons.append("buy take profit must be above entry price")
            if (
                context.line_available is not None
                and opening_risk
                and estimated_notional > context.line_available
            ):
                reasons.append("estimated notional exceeds available line")
            if context.reference_price and intent.price:
                deviation = (
                    abs(intent.price - context.reference_price) / context.reference_price * 100
                )
                if deviation > self.settings.max_price_deviation_pct:
                    reasons.append("limit price deviates too far from reference price")
            if opening_risk and intent.stop_loss is not None and price > 0:
                per_share_risk = max(0.0, price - intent.stop_loss)
                risk_value = per_share_risk * intent.quantity
                if context.portfolio_value and context.portfolio_value > 0:
                    estimated_risk_pct = risk_value / context.portfolio_value * 100
                    if estimated_risk_pct > self.settings.max_risk_per_trade_pct:
                        reasons.append("estimated stop-loss risk exceeds per-trade risk budget")
        else:
            if (
                context.quote_age_seconds is not None
                and context.quote_age_seconds > self.settings.market_data_stale_seconds
            ):
                reasons.append("prediction feed is stale")
            if estimated_notional <= 0:
                reasons.append("reference price is required for risk estimation")
            elif estimated_notional > self.settings.max_notional_per_order:
                reasons.append("order notional exceeds configured maximum")
            if estimated_notional > self.settings.prediction_max_order_usd:
                reasons.append("prediction order exceeds configured per-order USD limit")
            if (
                context.prediction_directional_residual is not None
                and context.prediction_directional_residual > self.settings.max_directional_residual
            ):
                reasons.append("directional residual exceeds configured maximum")
            if (
                context.prediction_complete_set_cost is not None
                and context.prediction_complete_set_cost > self.settings.max_complete_set_cost
            ):
                reasons.append("complete-set cost exceeds configured maximum")
            if (
                context.prediction_edge is not None
                and context.prediction_edge < self.settings.min_prediction_edge
            ):
                reasons.append("model edge is below minimum threshold")

        return RiskDecision(
            approved=not reasons,
            reasons=reasons,
            estimated_notional=estimated_notional,
            estimated_risk_pct=estimated_risk_pct,
        )


class PortfolioRiskManager:
    """Informational portfolio-level risk checks that complement RiskEngine."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_correlation(self, symbol: str, portfolio_positions: list[str]) -> list[str]:
        """Warn if adding a symbol would exceed correlation threshold.

        This is a simplified check: it flags if the symbol appears more than
        a configured ratio of the portfolio. Real correlation requires price
        history, so this acts as a concentration proxy.
        """
        reasons: list[str] = []
        total = len(portfolio_positions) + 1
        same_count = sum(1 for s in portfolio_positions if s == symbol)
        if total > 0 and (same_count + 1) / total > self.settings.max_correlation:
            reasons.append(
                f"symbol {symbol} correlation proxy exceeds max {self.settings.max_correlation:.2f}"
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
        if not self.settings.conflicting_strategies:
            return reasons
        conflicts = {
            pair.strip() for pair in self.settings.conflicting_strategies.split(",") if pair.strip()
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
        """Computes Historical Value-at-Risk (VaR) in USD."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        idx = max(0, int((1.0 - confidence_level) * len(sorted_returns)))
        loss_pct = abs(min(0.0, sorted_returns[idx]))
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
        reasons.extend(self.check_correlation(symbol, portfolio_positions))
        reasons.extend(
            self.check_allocation(symbol, portfolio_positions, self.settings.max_allocation_pct)
        )
        reasons.extend(self.check_conflict(strategy, active_strategies))
        return reasons

