"""
Freqtrade-compatible strategy framework for zksato.

This module provides a Freqtrade-inspired strategy interface (IStrategy) with
hyperoptable parameters, entry/exit signal generation, ROI tables, stoploss,
trailing stop, and protections. All strategies are advisory-only: order
execution always routes through RiskEngine and TradingService, preserving
zksato's safety invariants.

Safety invariants preserved:
- Paper mode is the default.
- Autonomous live-money execution is forbidden.
- No strategy may bypass RiskEngine or TradingService.
- Order creation is idempotent across retries and restarts.
- Stale/unknown market feed fails closed.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import pandas as pd

from zksato.domain import OrderIntent, OrderType, Side, SignalAction

logger = logging.getLogger(__name__)


# ── Parameter Types (Freqtrade-compatible hyperoptable parameters) ──────────


class Parameter:
    """Base class for hyperoptable strategy parameters.

    Parameters hold a default value and a search space range used by the
    hyperopt system. During normal (non-hyperopt) operation, the default
    value is used.
    """

    def __init__(
        self,
        default: Any,
        space: str = "buy",
        optimize: bool = True,
        load: bool = True,
    ) -> None:
        self.default = default
        self.space = space
        self.optimize = optimize
        self.load = load
        self._value = default

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        self._value = new_value

    @property
    def range(self) -> list[Any]:
        """Return the search space range (subclasses must implement)."""
        raise NotImplementedError


class IntParameter(Parameter):
    """Integer parameter with a bounded search space."""

    def __init__(
        self,
        low: int,
        high: int,
        default: int | None = None,
        space: str = "buy",
        optimize: bool = True,
        load: bool = True,
    ) -> None:
        if default is None:
            default = low
        super().__init__(default=default, space=space, optimize=optimize, load=load)
        self.low = low
        self.high = high

    @property
    def range(self) -> list[int]:
        return list(range(self.low, self.high + 1))


class DecimalParameter(Parameter):
    """Floating-point parameter with a bounded search space."""

    def __init__(
        self,
        low: float,
        high: float,
        default: float | None = None,
        decimals: int = 3,
        space: str = "buy",
        optimize: bool = True,
        load: bool = True,
    ) -> None:
        if default is None:
            default = low
        super().__init__(default=default, space=space, optimize=optimize, load=load)
        self.low = low
        self.high = high
        self.decimals = decimals

    @property
    def range(self) -> list[float]:
        step = 10**-self.decimals
        values: list[float] = []
        v = self.low
        while v <= self.high + 1e-9:
            values.append(round(v, self.decimals))
            v += step
        return values


class CategoricalParameter(Parameter):
    """Parameter with a predetermined set of choices."""

    def __init__(
        self,
        categories: list[Any],
        default: Any | None = None,
        space: str = "buy",
        optimize: bool = True,
        load: bool = True,
    ) -> None:
        if default is None:
            default = categories[0] if categories else None
        super().__init__(default=default, space=space, optimize=optimize, load=load)
        self.categories = list(categories)

    @property
    def range(self) -> list[Any]:
        return list(self.categories)


class BooleanParameter(CategoricalParameter):
    """Boolean parameter (shorthand for CategoricalParameter([True, False]))."""

    def __init__(
        self,
        default: bool = False,
        space: str = "buy",
        optimize: bool = True,
        load: bool = True,
    ) -> None:
        super().__init__(
            categories=[True, False],
            default=default,
            space=space,
            optimize=optimize,
            load=load,
        )


# ── Strategy Interface (Freqtrade IStrategy-compatible) ─────────────────────


class TradeDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class ExitReason(StrEnum):
    ROI = "roi"
    STOP_LOSS = "stop_loss"
    EXIT_SIGNAL = "exit_signal"
    TRAILING_STOP = "trailing_stop"
    FORCE_EXIT = "force_exit"
    PROTECTION = "protection"


@dataclass
class ROITableEntry:
    """A single entry in the minimal ROI table."""

    period: int  # minutes since entry
    profit: float  # profit ratio (e.g. 0.01 = 1%)


@dataclass
class TrailingStopConfig:
    """Trailing stop configuration."""

    enabled: bool = False
    positive: float | None = None  # trailing_stop_positive
    positive_offset: float | None = None  # trailing_stop_positive_offset
    only_offset_is_reached: bool = False


@dataclass
class Protection:
    """A protection rule."""

    method: str  # "CooldownPeriod", "StoplossGuard", etc.
    params: dict[str, Any] = field(default_factory=dict)


class IStrategy(ABC):
    """Freqtrade-compatible strategy interface.

    Strategies define indicators, entry/exit signals, risk parameters, and
    protections. All strategies are advisory: entry/exit signals are
    evaluated by the zksato RiskEngine before any order is submitted.
    """

    # ── Strategy metadata ──────────────────────────────────────────────
    name: str = "BaseStrategy"
    description: str = ""

    # ── Trading parameters ─────────────────────────────────────────────
    timeframe: str = "1m"
    stoploss: float = -0.10  # -10%
    minimal_roi: dict[int, float] | None = None  # {minutes: profit_ratio}
    trailing_stop: TrailingStopConfig | None = None
    max_open_trades: int = 3
    position_adjustment_enable: bool = False
    max_entry_position_adjustment: int = 1

    # ── Protections ────────────────────────────────────────────────────
    protections: list[Protection] | None = None

    # ── Hyperoptable parameters (subclasses define as class attributes) ────
    # Example:
    #   buy_rsi = IntParameter(20, 40, default=30, space="buy")
    #   buy_trigger = CategoricalParameter(
    #       ["bb_lower", "macd_cross"], default="bb_lower", space="buy"
    #   )

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = dict(config or {})
        self._hyperopt_params: dict[str, Parameter] = self._collect_hyperopt_params()

    def _collect_hyperopt_params(self) -> dict[str, Parameter]:
        """Collect all Parameter instances defined as class attributes."""
        params: dict[str, Parameter] = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Parameter):
                params[attr_name] = attr
        return params

    @property
    def hyperopt_params(self) -> dict[str, Parameter]:
        return self._hyperopt_params

    @property
    def roi_table(self) -> list[ROITableEntry]:
        """Convert minimal_roi dict to sorted ROITableEntry list."""
        if not self.minimal_roi:
            return []
        entries = [
            ROITableEntry(period=int(k), profit=float(v)) for k, v in self.minimal_roi.items()
        ]
        entries.sort(key=lambda e: e.period)
        return entries

    # ── Abstract methods (subclasses must implement) ───────────────────

    @abstractmethod
    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        """Calculate all indicators used by the strategy.

        Args:
            dataframe: OHLCV data with columns ['date', 'open', 'high', 'low', 'close', 'volume'].
            metadata: Dict with 'pair', 'timeframe', etc.

        Returns:
            DataFrame with indicator columns added.
        """
        ...

    @abstractmethod
    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        """Define entry signals.

        Sets dataframe['enter_long'] = 1 for long entries and
        dataframe['enter_short'] = 1 for short entries.
        """
        ...

    @abstractmethod
    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        """Define exit signals.

        Sets dataframe['exit_long'] = 1 for long exits and
        dataframe['exit_short'] = 1 for short exits.
        """
        ...

    # ── Optional hooks ─────────────────────────────────────────────────

    def custom_stoploss(
        self,
        pair: str,
        trade: Any,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
    ) -> float:
        """Custom stoploss calculation. Returns stoploss ratio (e.g. -0.05)."""
        return self.stoploss

    def custom_exit(
        self,
        pair: str,
        trade: Any,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
    ) -> str | None:
        """Custom exit signal. Returns exit reason string or None."""
        return None

    def custom_entry_price(
        self,
        pair: str,
        current_time: datetime,
        proposed_rate: float,
    ) -> float:
        """Custom entry price. Returns adjusted entry price."""
        return proposed_rate

    def custom_exit_price(
        self,
        pair: str,
        trade: Any,
        current_time: datetime,
        proposed_rate: float,
    ) -> float:
        """Custom exit price. Returns adjusted exit price."""
        return proposed_rate

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: OrderType,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
    ) -> bool:
        """Pre-entry confirmation. Return False to veto the entry."""
        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Any,
        order_type: OrderType,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
    ) -> bool:
        """Pre-exit confirmation. Return False to veto the exit."""
        return True

    # ── Conversion to zksato OrderIntent ───────────────────────────────

    def signal_to_intent(
        self,
        symbol: str,
        action: SignalAction,
        quantity: float,
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        client_order_id: str | None = None,
    ) -> OrderIntent:
        """Convert a strategy signal into a zksato OrderIntent.

        This is the only path from a strategy signal to a zksato order.
        The OrderIntent is then evaluated by RiskEngine before execution.
        """
        return OrderIntent(
            symbol=symbol,
            side=Side.BUY if action == SignalAction.BUY else Side.SELL,
            quantity=quantity,
            order_type=OrderType.LIMIT if price is not None else OrderType.MARKET,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            client_order_id=client_order_id,
            source=f"strategy:{self.name}",
        )

    # ── Hyperopt parameter access ──────────────────────────────────────

    def get_hyperopt_param(self, name: str) -> Any:
        """Get the current value of a hyperoptable parameter."""
        param = self._hyperopt_params.get(name)
        if param is None:
            raise KeyError(f"No hyperopt parameter '{name}' in strategy '{self.name}'")
        return param.value

    def set_hyperopt_param(self, name: str, value: Any) -> None:
        """Set the value of a hyperoptable parameter."""
        param = self._hyperopt_params.get(name)
        if param is None:
            raise KeyError(f"No hyperopt parameter '{name}' in strategy '{self.name}'")
        param.value = value

    def get_hyperopt_spaces(self) -> dict[str, list[str]]:
        """Group hyperoptable parameters by space."""
        spaces: dict[str, list[str]] = {}
        for name, param in self._hyperopt_params.items():
            spaces.setdefault(param.space, []).append(name)
        return spaces


# ── Strategy Registry ──────────────────────────────────────────────────


class StrategyRegistry:
    """Registry for strategy classes."""

    def __init__(self) -> None:
        self._strategies: dict[str, type[IStrategy]] = {}

    def register(self, strategy_class: type[IStrategy]) -> None:
        name = strategy_class.name
        self._strategies[name] = strategy_class
        logger.info("Registered strategy: %s", name)

    def get(self, name: str) -> type[IStrategy] | None:
        return self._strategies.get(name)

    def list(self) -> list[str]:
        return sorted(self._strategies.keys())

    def instantiate(self, name: str, config: dict[str, Any] | None = None) -> IStrategy | None:
        strategy_class = self.get(name)
        if strategy_class is None:
            return None
        return strategy_class(config=config)


# Global registry instance
strategy_registry = StrategyRegistry()


def register_strategy(strategy_class: type[IStrategy]) -> type[IStrategy]:
    """Decorator to register a strategy class."""
    strategy_registry.register(strategy_class)
    return strategy_class
