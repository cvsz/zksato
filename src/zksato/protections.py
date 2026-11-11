"""
Protection mechanisms for trading strategies.

Protections are rules that can pause or restrict trading based on market
conditions or recent trade outcomes. Inspired by Freqtrade's protection system.

Protections are evaluated BEFORE order submission and can veto trades.
They never bypass RiskEngine — they are an additional layer of safety.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from zksato.domain import Side

logger = logging.getLogger(__name__)


@dataclass
class TradeContext:
    """Context for protection evaluation."""

    symbol: str
    side: Side
    order_type: Any
    amount: float
    price: float | None
    current_time: datetime
    recent_trades: list[dict[str, Any]] = field(default_factory=list)
    portfolio_value: float = 0.0
    daily_pnl_pct: float = 0.0


class ProtectionResult:
    """Result of a protection check."""

    def __init__(self, allowed: bool, reason: str = "") -> None:
        self.allowed = allowed
        self.reason = reason


class Protection(ABC):
    """Base class for protection mechanisms."""

    name: str = "BaseProtection"

    @abstractmethod
    def evaluate(self, context: TradeContext) -> ProtectionResult:
        """Evaluate whether a trade should be allowed.

        Returns ProtectionResult with allowed=True/False and an optional reason.
        """
        ...


class CooldownPeriodProtection(Protection):
    """Prevents trading for a period after a trade exit (cooldown)."""

    name = "CooldownPeriod"

    def __init__(
        self,
        stop_duration_candles: int = 4,
        candle_duration_seconds: int = 60,
    ) -> None:
        self.stop_duration_candles = stop_duration_candles
        self.candle_duration_seconds = candle_duration_seconds
        self._last_trade_time: dict[str, datetime] = {}

    def evaluate(self, context: TradeContext) -> ProtectionResult:
        symbol = context.symbol
        if symbol not in self._last_trade_time:
            return ProtectionResult(allowed=True)

        cooldown_seconds = self.stop_duration_candles * self.candle_duration_seconds
        elapsed = (context.current_time - self._last_trade_time[symbol]).total_seconds()

        if elapsed < cooldown_seconds:
            remaining = cooldown_seconds - elapsed
            return ProtectionResult(
                allowed=False,
                reason=f"cooldown period active ({remaining:.0f}s remaining)",
            )
        return ProtectionResult(allowed=True)

    def record_trade_exit(self, symbol: str, exit_time: datetime) -> None:
        """Record a trade exit to start cooldown."""
        self._last_trade_time[symbol] = exit_time


class StoplossGuardProtection(Protection):
    """Pauses trading after consecutive losses (stoploss guard)."""

    name = "StoplossGuard"

    def __init__(
        self,
        lookback_period_candles: int = 24 * 3,  # 3 days of 1-hour candles
        trade_limit: int = 4,
        stop_duration_candles: int = 4,
        only_per_pair: bool = False,
        candle_duration_seconds: int = 3600,
    ) -> None:
        self.lookback_period_candles = lookback_period_candles
        self.trade_limit = trade_limit
        self.stop_duration_candles = stop_duration_candles
        self.only_per_pair = only_per_pair
        self.candle_duration_seconds = candle_duration_seconds
        self._recent_losses: dict[str, list[datetime]] = {}
        self._stop_until: dict[str, datetime] = {}

    def evaluate(self, context: TradeContext) -> ProtectionResult:
        symbol = context.symbol if not self.only_per_pair else "global"
        current_time = context.current_time

        # Check if we're currently in a stop period
        stop_until = self._stop_until.get(symbol)
        if stop_until is not None and current_time < stop_until:
            remaining = (stop_until - current_time).total_seconds()
            return ProtectionResult(
                allowed=False,
                reason=f"stoploss guard active ({remaining:.0f}s remaining)",
            )
        if stop_until is not None and current_time >= stop_until:
            # Stop period has expired
            del self._stop_until[symbol]

        # Count recent losses
        lookback_start = current_time - timedelta(
            seconds=self.lookback_period_candles * self.candle_duration_seconds
        )
        recent_losses = self._recent_losses.get(symbol, [])
        recent_losses = [t for t in recent_losses if t >= lookback_start]
        self._recent_losses[symbol] = recent_losses

        if len(recent_losses) >= self.trade_limit:
            # Trigger stop period
            stop_until = current_time + timedelta(
                seconds=self.stop_duration_candles * self.candle_duration_seconds
            )
            self._stop_until[symbol] = stop_until
            return ProtectionResult(
                allowed=False,
                reason=f"stoploss guard triggered ({len(recent_losses)} losses in lookback)",
            )

        return ProtectionResult(allowed=True)

    def record_trade_loss(self, symbol: str, loss_time: datetime) -> None:
        """Record a losing trade."""
        key = symbol if not self.only_per_pair else "global"
        self._recent_losses.setdefault(key, []).append(loss_time)


class DrawdownProtection(Protection):
    """Pauses trading when daily drawdown exceeds a threshold."""

    name = "DrawdownProtection"

    def __init__(
        self,
        max_daily_drawdown_pct: float = 5.0,
    ) -> None:
        self.max_daily_drawdown_pct = max_daily_drawdown_pct

    def evaluate(self, context: TradeContext) -> ProtectionResult:
        if context.daily_pnl_pct <= -abs(self.max_daily_drawdown_pct):
            return ProtectionResult(
                allowed=False,
                reason=f"daily drawdown limit reached ({context.daily_pnl_pct:.2f}%)",
            )
        return ProtectionResult(allowed=True)


class ProtectionManager:
    """Manages multiple protection mechanisms."""

    def __init__(self, protections: list[Protection] | None = None) -> None:
        self.protections: list[Protection] = list(protections or [])

    def add(self, protection: Protection) -> None:
        self.protections.append(protection)

    def evaluate_all(self, context: TradeContext) -> ProtectionResult:
        """Evaluate all protections. Returns False if any protection blocks."""
        for protection in self.protections:
            result = protection.evaluate(context)
            if not result.allowed:
                return ProtectionResult(
                    allowed=False,
                    reason=f"{protection.name}: {result.reason}",
                )
        return ProtectionResult(allowed=True)

    def record_trade_exit(self, symbol: str, exit_time: datetime, was_loss: bool = False) -> None:
        """Record a trade exit for protection tracking."""
        for protection in self.protections:
            if isinstance(protection, CooldownPeriodProtection):
                protection.record_trade_exit(symbol, exit_time)
            if isinstance(protection, StoplossGuardProtection) and was_loss:
                protection.record_trade_loss(symbol, exit_time)
