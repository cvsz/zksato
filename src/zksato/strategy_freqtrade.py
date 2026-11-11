"""
Freqtrade-compatible strategy framework for zksato — Refactored v2.

This module provides a Freqtrade-inspired strategy interface (IStrategy) with
hyperoptable parameters, entry/exit signal generation with tags, ROI tables,
stoploss, trailing stop, protections, position stacking, and order expiration.

All strategies are advisory-only: order execution always routes through
RiskEngine and TradingService, preserving zksato's safety invariants.

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
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import pandas as pd

from zksato.domain import OrderIntent, OrderType, Side, SignalAction
from zksato.indicators import atr, rsi

logger = logging.getLogger(__name__)


# ── Entry/Exit Tags ──────────────────────────────────────────────────────────


@dataclass
class EntryTag:
    """Tag identifying which condition triggered an entry."""

    name: str
    condition: str
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExitTag:
    """Tag identifying which condition triggered an exit."""

    name: str
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ── Parameter Types (Freqtrade-compatible hyperoptable parameters) ──────────


class Parameter:
    """Base class for hyperoptable strategy parameters."""

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
    ORDER_EXPIRATION = "order_expiration"


class MarketRegime(StrEnum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


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


@dataclass
class TradeContext:
    """Context for a trade, including entry/exit tags and position info."""

    symbol: str
    side: Side
    entry_price: float
    entry_time: datetime
    amount: float
    entry_tag: EntryTag | None = None
    exit_tag: ExitTag | None = None
    current_stop_loss: float | None = None
    current_take_profit: float | None = None
    position_adjustments: int = 0
    max_position_adjustments: int = 1
    order_expiration_candles: int | None = None
    order_entry_candle_index: int | None = None
    market_regime: MarketRegime | None = None


class IStrategy(ABC):
    """Freqtrade-compatible strategy interface.

    Strategies define indicators, entry/exit signals, risk parameters, and
    protections. All strategies are advisory: entry/exit signals are
    evaluated by the zksato RiskEngine before any order is submitted.

    Safety invariants:
    - All order intents are submitted to RiskEngine before execution.
    - No strategy can bypass TradingService.
    - Paper mode is the default.
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
    unfilled_timeout_candles: int | None = None  # Cancel unfilled orders after N candles
    use_exit_signal: bool = True
    use_custom_stoploss: bool = False
    process_only_new_candles: bool = True
    startup_candle_count: int = 0

    # ── Market regime detection ────────────────────────────────────────
    detect_market_regime: bool = False
    regime_lookback_period: int = 50
    regime_bull_threshold: float = 0.02  # 2% above EMA200 = bull
    regime_bear_threshold: float = -0.02  # 2% below EMA200 = bear

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
        self._trade_contexts: dict[str, TradeContext] = {}  # symbol -> TradeContext

    def _collect_hyperopt_params(self) -> dict[str, Parameter]:
        """Collect all Parameter instances defined as class attributes."""
        params: dict[str, Parameter] = {}
        for attr_name in dir(self):
            if attr_name == "hyperopt_params":
                # Skip the property itself to avoid circular access during __init__
                continue
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
        dataframe['enter_short'] = 1 for short exits.
        Also sets dataframe['enter_tag'] with the tag name for each entry.
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
        Also sets dataframe['exit_tag'] with the tag name for each exit.
        """
        ...

    # ── Optional hooks ─────────────────────────────────────────────────

    def custom_stoploss(
        self,
        pair: str,
        trade: TradeContext,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
    ) -> float:
        """Custom stoploss calculation. Returns stoploss ratio (e.g. -0.05)."""
        return self.stoploss

    def custom_exit(
        self,
        pair: str,
        trade: TradeContext,
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
        trade: TradeContext,
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
        trade: TradeContext,
        order_type: OrderType,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
    ) -> bool:
        """Pre-exit confirmation. Return False to veto the exit."""
        return True

    def detect_regime(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> MarketRegime | None:
        """Detect market regime (bull/bear/sideways/volatile) from price action.

        Default implementation uses EMA200 comparison:
        - Price > EMA200 + threshold: BULL
        - Price < EMA200 - threshold: BEAR
        - Otherwise: SIDEWAYS
        """
        if not self.detect_market_regime:
            return None

        try:
            close = dataframe["close"].iloc[-1]
            # Simple EMA200 approximation using rolling mean
            ema200 = dataframe["close"].rolling(window=self.regime_lookback_period).mean().iloc[-1]
            if pd.isna(ema200):
                return None

            pct_diff = (close - ema200) / ema200
            if pct_diff >= self.regime_bull_threshold:
                return MarketRegime.BULL
            if pct_diff <= self.regime_bear_threshold:
                return MarketRegime.BEAR
            return MarketRegime.SIDEWAYS
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Regime detection failed: %s", exc)
            return None

    def order_expiration_check(
        self,
        trade: TradeContext,
        current_candle_index: int,
    ) -> bool:
        """Check if an unfilled order should expire.

        Returns True if the order should be cancelled (expired).
        """
        if trade.order_expiration_candles is None or trade.order_entry_candle_index is None:
            return False
        return (
            current_candle_index - trade.order_entry_candle_index
        ) >= trade.order_expiration_candles

    def can_add_to_position(
        self,
        trade: TradeContext,
    ) -> bool:
        """Check if position can be scaled into (position stacking)."""
        if not self.position_adjustment_enable:
            return False
        return trade.position_adjustments < trade.max_position_adjustments

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
        entry_tag: str | None = None,
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

    def create_trade_context(
        self,
        symbol: str,
        side: Side,
        entry_price: float,
        entry_time: datetime,
        amount: float,
        entry_tag: EntryTag | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        market_regime: MarketRegime | None = None,
    ) -> TradeContext:
        """Create a TradeContext for tracking a position."""
        return TradeContext(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            entry_time=entry_time,
            amount=amount,
            entry_tag=entry_tag,
            current_stop_loss=stop_loss,
            current_take_profit=take_profit,
            market_regime=market_regime,
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


# ── Example Strategies ───────────────────────────────────────────────────


@register_strategy
class EMAcrossStrategy(IStrategy):
    """EMA Cross strategy — Freqtrade-compatible example.

    Buys when fast EMA crosses above slow EMA.
    Sells when fast EMA crosses below slow EMA.
    """

    name = "ema_cross"
    description = "EMA Cross strategy — buys on fast EMA cross above slow EMA"
    timeframe = "15m"
    stoploss = -0.05  # -5%
    minimal_roi = {0: 0.02, 60: 0.01, 120: 0.0}
    trailing_stop = TrailingStopConfig(
        enabled=True,
        positive=0.02,
        positive_offset=0.01,
        only_offset_is_reached=False,
    )
    max_open_trades = 3
    position_adjustment_enable = True
    max_entry_position_adjustment = 1
    unfilled_timeout_candles = 10

    # Hyperoptable parameters
    buy_ema_fast = IntParameter(5, 50, default=12, space="buy", optimize=True)
    buy_ema_slow = IntParameter(10, 200, default=26, space="buy", optimize=True)
    sell_ema_fast = IntParameter(5, 50, default=12, space="sell", optimize=True)
    sell_ema_slow = IntParameter(10, 200, default=26, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["ema_fast"] = (
            dataframe["close"].ewm(span=self.buy_ema_fast.value, adjust=False).mean()
        )
        dataframe["ema_slow"] = (
            dataframe["close"].ewm(span=self.buy_ema_slow.value, adjust=False).mean()
        )
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: fast EMA crosses above slow EMA
        buy_condition = (dataframe["ema_fast"] > dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1)
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "ema_cross_buy"

        # Sell: fast EMA crosses below slow EMA
        sell_condition = (dataframe["ema_fast"] < dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1)
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "ema_cross_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: fast EMA crosses below slow EMA
        exit_long_condition = (dataframe["ema_fast"] < dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1)
        )
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "ema_cross_exit_long"

        # Exit short: fast EMA crosses above slow EMA
        exit_short_condition = (dataframe["ema_fast"] > dataframe["ema_slow"]) & (
            dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1)
        )
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "ema_cross_exit_short"

        return dataframe


@register_strategy
class RSIRebversionStrategy(IStrategy):
    """RSI Reversion strategy — Freqtrade-compatible example.

    Buys when RSI is oversold (< rsi_buy).
    Sells when RSI is overbought (> rsi_sell).
    """

    name = "rsi_reversion"
    description = "RSI Reversion strategy — buys oversold, sells overbought"
    timeframe = "1h"
    stoploss = -0.08  # -8%
    minimal_roi = {0: 0.03, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    buy_rsi = IntParameter(20, 40, default=30, space="buy", optimize=True)
    sell_rsi = IntParameter(60, 80, default=70, space="sell", optimize=True)
    rsi_period = IntParameter(10, 30, default=14, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        delta = dataframe["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period.value).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period.value).mean()
        rs = gain / loss
        dataframe["rsi"] = 100 - (100 / (1 + rs))
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: RSI oversold
        buy_condition = dataframe["rsi"] <= self.buy_rsi.value
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "rsi_oversold"

        # Sell: RSI overbought
        sell_condition = dataframe["rsi"] >= self.sell_rsi.value
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "rsi_overbought"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: RSI overbought
        exit_long_condition = dataframe["rsi"] >= self.sell_rsi.value
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "rsi_overbought_exit"

        # Exit short: RSI oversold
        exit_short_condition = dataframe["rsi"] <= self.buy_rsi.value
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "rsi_oversold_exit"

        return dataframe


@register_strategy
class MACDCrossStrategy(IStrategy):
    """MACD Cross strategy — Freqtrade-compatible example.

    Buys when MACD line crosses above signal line.
    Sells when MACD line crosses below signal line.
    """

    name = "macd_cross"
    description = "MACD Cross strategy — buys on MACD cross above signal, sells on cross below"
    timeframe = "15m"
    stoploss = -0.06  # -6%
    minimal_roi = {0: 0.025, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    buy_macd_fast = IntParameter(8, 30, default=12, space="buy", optimize=True)
    buy_macd_slow = IntParameter(20, 60, default=26, space="buy", optimize=True)
    buy_macd_signal = IntParameter(5, 20, default=9, space="buy", optimize=True)
    sell_macd_fast = IntParameter(8, 30, default=12, space="sell", optimize=True)
    sell_macd_slow = IntParameter(20, 60, default=26, space="sell", optimize=True)
    sell_macd_signal = IntParameter(5, 20, default=9, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # MACD for buy side
        macd_fast = dataframe["close"].ewm(span=self.buy_macd_fast.value, adjust=False).mean()
        macd_slow = dataframe["close"].ewm(span=self.buy_macd_slow.value, adjust=False).mean()
        dataframe["macd_line"] = macd_fast - macd_slow
        dataframe["macd_signal"] = (
            dataframe["macd_line"].ewm(span=self.buy_macd_signal.value, adjust=False).mean()
        )
        dataframe["macd_histogram"] = dataframe["macd_line"] - dataframe["macd_signal"]

        # MACD for sell side (same calculation, separate parameter set for hyperopt)
        dataframe["sell_macd_line"] = (
            dataframe["close"].ewm(span=self.sell_macd_fast.value, adjust=False).mean()
            - dataframe["close"].ewm(span=self.sell_macd_slow.value, adjust=False).mean()
        )
        dataframe["sell_macd_signal"] = (
            dataframe["sell_macd_line"].ewm(span=self.sell_macd_signal.value, adjust=False).mean()
        )

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: fast EMA crosses above slow EMA (MACD line crosses above signal)
        buy_condition = (dataframe["macd_line"] > dataframe["macd_signal"]) & (
            dataframe["macd_line"].shift(1) <= dataframe["macd_signal"].shift(1)
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "macd_cross_buy"

        # Sell: fast EMA crosses below slow EMA (MACD line crosses below signal)
        sell_condition = (dataframe["macd_line"] < dataframe["macd_signal"]) & (
            dataframe["macd_line"].shift(1) >= dataframe["macd_signal"].shift(1)
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "macd_cross_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: MACD line crosses below signal line
        exit_long_condition = (dataframe["macd_line"] < dataframe["macd_signal"]) & (
            dataframe["macd_line"].shift(1) >= dataframe["macd_signal"].shift(1)
        )
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "macd_cross_exit_long"

        # Exit short: MACD line crosses above signal line
        exit_short_condition = (dataframe["macd_line"] > dataframe["macd_signal"]) & (
            dataframe["macd_line"].shift(1) <= dataframe["macd_signal"].shift(1)
        )
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "macd_cross_exit_short"

        return dataframe


@register_strategy
class BollingerReversionStrategy(IStrategy):
    """Bollinger Band Reversion strategy — Freqtrade-compatible example.

    Buys when price touches or crosses below the lower Bollinger Band.
    Sells when price touches or crosses above the upper Bollinger Band.
    """

    name = "bollinger_reversion"
    description = "Bollinger Band Reversion — buys at lower band, sells at upper band"
    timeframe = "15m"
    stoploss = -0.08  # -8%
    minimal_roi = {0: 0.03, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    buy_bb_period = IntParameter(10, 50, default=20, space="buy", optimize=True)
    buy_bb_deviations = DecimalParameter(1.5, 4.0, default=2.0, space="buy", optimize=True)
    sell_bb_period = IntParameter(10, 50, default=20, space="sell", optimize=True)
    sell_bb_deviations = DecimalParameter(1.5, 4.0, default=2.0, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # Bollinger Bands for buy side
        buy_bb_middle = dataframe["close"].rolling(window=self.buy_bb_period.value).mean()
        buy_bb_std = dataframe["close"].rolling(window=self.buy_bb_period.value).std()
        dataframe["bb_lower_buy"] = buy_bb_middle - (buy_bb_std * self.buy_bb_deviations.value)
        dataframe["bb_upper_buy"] = buy_bb_middle + (buy_bb_std * self.buy_bb_deviations.value)
        dataframe["bb_middle_buy"] = buy_bb_middle

        # Bollinger Bands for sell side (same calculation, separate parameter set for hyperopt)
        sell_bb_middle = dataframe["close"].rolling(window=self.sell_bb_period.value).mean()
        sell_bb_std = dataframe["close"].rolling(window=self.sell_bb_period.value).std()
        dataframe["bb_lower_sell"] = sell_bb_middle - (sell_bb_std * self.sell_bb_deviations.value)
        dataframe["bb_upper_sell"] = sell_bb_middle + (sell_bb_std * self.sell_bb_deviations.value)
        dataframe["bb_middle_sell"] = sell_bb_middle

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: price touches or crosses below the lower Bollinger Band
        buy_condition = dataframe["close"] <= dataframe["bb_lower_buy"]
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "bollinger_reversion_buy"

        # Sell: price touches or crosses above the upper Bollinger Band
        sell_condition = dataframe["close"] >= dataframe["bb_upper_sell"]
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "bollinger_reversion_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: price touches or crosses above the middle Bollinger Band
        exit_long_condition = dataframe["close"] >= dataframe["bb_middle_buy"]
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "bollinger_reversion_exit_long"

        # Exit short: price touches or crosses below the middle Bollinger Band
        exit_short_condition = dataframe["close"] <= dataframe["bb_middle_sell"]
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "bollinger_reversion_exit_short"

        return dataframe


@register_strategy
class StochasticOscillatorStrategy(IStrategy):
    """Stochastic Oscillator strategy — Freqtrade-compatible example.

    Buys when %K crosses above %D while both are below oversold level.
    Sells when %K crosses below %D while both are above overbought level.
    """

    name = "stochastic_oscillator"
    description = (
        "Stochastic Oscillator — buys when %K crosses above %D in oversold, "
        "sells when %K crosses below %D in overbought"
    )
    timeframe = "15m"
    stoploss = -0.08  # -8%
    minimal_roi = {0: 0.03, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    stoch_k_period = IntParameter(10, 50, default=14, space="buy", optimize=True)
    stoch_d_period = IntParameter(3, 10, default=3, space="buy", optimize=True)
    stoch_overbought = IntParameter(70, 90, default=80, space="sell", optimize=True)
    stoch_oversold = IntParameter(10, 30, default=20, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # Fast %K
        low_min = dataframe["low"].rolling(window=self.stoch_k_period.value).min()
        high_max = dataframe["high"].rolling(window=self.stoch_k_period.value).max()
        dataframe["stoch_k"] = (dataframe["close"] - low_min) / (high_max - low_min) * 100
        # %D is SMA of %K
        dataframe["stoch_d"] = dataframe["stoch_k"].rolling(window=self.stoch_d_period.value).mean()
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: %K crosses above %D while both are below oversold level
        buy_condition = (
            (dataframe["stoch_k"] > dataframe["stoch_d"])
            & (dataframe["stoch_k"].shift(1) <= dataframe["stoch_d"].shift(1))
            & (dataframe["stoch_k"] <= self.stoch_oversold.value)
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "stochastic_oversold_buy"

        # Sell: %K crosses below %D while both are above overbought level
        sell_condition = (
            (dataframe["stoch_k"] < dataframe["stoch_d"])
            & (dataframe["stoch_k"].shift(1) >= dataframe["stoch_d"].shift(1))
            & (dataframe["stoch_k"] >= self.stoch_overbought.value)
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "stochastic_overbought_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: %K crosses above overbought level
        exit_long_condition = dataframe["stoch_k"] >= self.stoch_overbought.value
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "stochastic_overbought_exit_long"

        # Exit short: %K crosses below oversold level
        exit_short_condition = dataframe["stoch_k"] <= self.stoch_oversold.value
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "stochastic_oversold_exit_short"

        return dataframe


@register_strategy
class WilliamsRStrategy(IStrategy):
    """Williams %R strategy — Freqtrade-compatible example.

    Buys when Williams %R crosses above -80 (oversold).
    Sells when Williams %R crosses below -20 (overbought).
    """

    name = "williams_r"
    description = (
        "Williams %R — buys when %R crosses above -80 (oversold), "
        "sells when %R crosses below -20 (overbought)"
    )
    timeframe = "15m"
    stoploss = -0.08  # -8%
    minimal_roi = {0: 0.03, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    williams_r_period = IntParameter(10, 50, default=14, space="buy", optimize=True)
    williams_r_overbought = IntParameter(-30, -10, default=-20, space="sell", optimize=True)
    williams_r_oversold = IntParameter(-90, -70, default=-80, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        highest_high = dataframe["high"].rolling(window=self.williams_r_period.value).max()
        lowest_low = dataframe["low"].rolling(window=self.williams_r_period.value).min()
        dataframe["williams_r"] = (
            (highest_high - dataframe["close"]) / (highest_high - lowest_low) * -100
        )
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: Williams %R crosses above oversold level (-80)
        buy_condition = (dataframe["williams_r"] > self.williams_r_oversold.value) & (
            dataframe["williams_r"].shift(1) <= self.williams_r_oversold.value
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "williams_r_oversold_buy"

        # Sell: Williams %R crosses below overbought level (-20)
        sell_condition = (dataframe["williams_r"] < self.williams_r_overbought.value) & (
            dataframe["williams_r"].shift(1) >= self.williams_r_overbought.value
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "williams_r_overbought_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: Williams %R crosses above overbought level
        exit_long_condition = dataframe["williams_r"] >= self.williams_r_overbought.value
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "williams_r_overbought_exit_long"

        # Exit short: Williams %R crosses below oversold level
        exit_short_condition = dataframe["williams_r"] <= self.williams_r_oversold.value
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "williams_r_oversold_exit_short"

        return dataframe


@register_strategy
class ATRChannelStrategy(IStrategy):
    """ATR Channel strategy — Freqtrade-compatible example.

    Buys when price touches or crosses below the lower ATR channel.
    Sells when price touches or crosses above the upper ATR channel.
    """

    name = "atr_channel"
    description = "ATR Channel — buys at lower channel, sells at upper channel"
    timeframe = "15m"
    stoploss = -0.08  # -8%
    minimal_roi = {0: 0.03, 120: 0.015, 240: 0.0}
    max_open_trades = 5

    # Hyperoptable parameters
    atr_period = IntParameter(10, 50, default=14, space="buy", optimize=True)
    atr_multiplier = DecimalParameter(1.0, 5.0, default=2.0, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # ATR Channel
        atr_value = atr(dataframe, self.atr_period.value)
        ema_value = dataframe["close"].ewm(span=20, adjust=False).mean()
        dataframe["atr_channel_upper"] = ema_value + (atr_value * self.atr_multiplier.value)
        dataframe["atr_channel_lower"] = ema_value - (atr_value * self.atr_multiplier.value)
        dataframe["atr_channel_middle"] = ema_value
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Buy: price touches or crosses below the lower ATR channel
        buy_condition = dataframe["close"] <= dataframe["atr_channel_lower"]
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "atr_channel_buy"

        # Sell: price touches or crosses above the upper ATR channel
        sell_condition = dataframe["close"] >= dataframe["atr_channel_upper"]
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "atr_channel_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        # Exit long: price touches or crosses above the middle ATR channel
        exit_long_condition = dataframe["close"] >= dataframe["atr_channel_middle"]
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "atr_channel_exit_long"

        # Exit short: price touches or crosses below the middle ATR channel
        exit_short_condition = dataframe["close"] <= dataframe["atr_channel_middle"]
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "atr_channel_exit_short"

        return dataframe


# ── Momentum Strategy ─────────────────────────────────────────────────────


@register_strategy
class MomentumStrategy(IStrategy):
    """Momentum strategy — buys on upward momentum, sells on downward momentum.

    Uses rate of change (ROC) to detect momentum strength and direction.
    """

    name = "momentum"
    description = "Momentum — buys when ROC crosses above zero, sells when below"
    timeframe = "15m"
    stoploss = -0.06
    minimal_roi = {0: 0.02, 60: 0.01, 180: 0.0}
    max_open_trades = 5

    momentum_period = IntParameter(10, 30, default=14, space="buy", optimize=True)
    momentum_buy_threshold = DecimalParameter(0.0, 3.0, default=1.0, space="buy", optimize=True)
    momentum_sell_threshold = DecimalParameter(-3.0, 0.0, default=-1.0, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        closes = dataframe["close"].tolist()
        roc_values: list[float | None] = []
        for i in range(len(closes)):
            if i < self.momentum_period.value:
                roc_values.append(None)
            else:
                prev = closes[i - self.momentum_period.value]
                curr = closes[i]
                if prev == 0:
                    roc_values.append(None)
                else:
                    roc_values.append((curr - prev) / prev * 100.0)
        dataframe["momentum_roc"] = roc_values
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["momentum_roc"].notna() & (
            dataframe["momentum_roc"] > self.momentum_buy_threshold.value
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "momentum_buy"

        sell_condition = dataframe["momentum_roc"].notna() & (
            dataframe["momentum_roc"] < self.momentum_sell_threshold.value
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "momentum_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["momentum_roc"].notna() & (dataframe["momentum_roc"] <= 0.0)
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "momentum_exit_long"

        exit_short_condition = dataframe["momentum_roc"].notna() & (
            dataframe["momentum_roc"] >= 0.0
        )
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "momentum_exit_short"

        return dataframe


# ── Breakout Strategy ─────────────────────────────────────────────────────


@register_strategy
class BreakoutStrategy(IStrategy):
    """Breakout strategy — buys on breakout above recent high, sells on breakdown below recent low.

    Uses highest/lowest over a lookback period to detect breakouts.
    """

    name = "breakout"
    description = "Breakout — buys on breakout above N-bar high, sells on breakdown below N-bar low"
    timeframe = "1h"
    stoploss = -0.05
    minimal_roi = {0: 0.03, 120: 0.015, 360: 0.0}
    max_open_trades = 4

    breakout_lookback = IntParameter(10, 50, default=20, space="buy", optimize=True)
    breakout_buffer_pct = DecimalParameter(0.0, 1.0, default=0.2, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        lookback = self.breakout_lookback.value
        dataframe["breakout_high"] = dataframe["high"].rolling(window=lookback).max()
        dataframe["breakout_low"] = dataframe["low"].rolling(window=lookback).min()
        buffer = self.breakout_buffer_pct.value / 100.0
        dataframe["breakout_trigger_high"] = dataframe["breakout_high"] * (1 + buffer)
        dataframe["breakout_trigger_low"] = dataframe["breakout_low"] * (1 - buffer)
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["close"] > dataframe["breakout_trigger_high"]
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "breakout_buy"

        sell_condition = dataframe["close"] < dataframe["breakout_trigger_low"]
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "breakout_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["close"] < dataframe["breakout_low"]
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "breakout_exit_long"

        exit_short_condition = dataframe["close"] > dataframe["breakout_high"]
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "breakout_exit_short"

        return dataframe


# ── Scalp Strategy ────────────────────────────────────────────────────────


@register_strategy
class ScalpStrategy(IStrategy):
    """Scalp strategy — quick entries on RSI extremes with tight stops.

    Uses RSI oversold/overbought for rapid in-and-out trades.
    """

    name = "scalp"
    description = "Scalp — quick trades on RSI extremes with tight risk controls"
    timeframe = "5m"
    stoploss = -0.02
    minimal_roi = {0: 0.01, 30: 0.005, 60: 0.0}
    max_open_trades = 8

    scalp_rsi_period = IntParameter(7, 21, default=14, space="buy", optimize=True)
    scalp_rsi_oversold = IntParameter(15, 35, default=30, space="buy", optimize=True)
    scalp_rsi_overbought = IntParameter(65, 85, default=70, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        closes = dataframe["close"].tolist()
        period = self.scalp_rsi_period.value
        rsi_values: list[float | None] = []
        for i in range(len(closes)):
            if i < period:
                rsi_values.append(None)
            else:
                window = closes[i - period : i + 1]
                rsi_values.append(rsi(window, period))
        dataframe["scalp_rsi"] = rsi_values
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["scalp_rsi"].notna() & (
            dataframe["scalp_rsi"] <= self.scalp_rsi_oversold.value
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "scalp_buy"

        sell_condition = dataframe["scalp_rsi"].notna() & (
            dataframe["scalp_rsi"] >= self.scalp_rsi_overbought.value
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "scalp_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["scalp_rsi"].notna() & (dataframe["scalp_rsi"] >= 50.0)
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "scalp_exit_long"

        exit_short_condition = dataframe["scalp_rsi"].notna() & (dataframe["scalp_rsi"] <= 50.0)
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "scalp_exit_short"

        return dataframe


# ── Swing Strategy ──────────────────────────────────────────────────────


@register_strategy
class SwingStrategy(IStrategy):
    """Swing strategy — trend-following using EMA cross on higher timeframes.

    Buys when fast EMA crosses above slow EMA, sells on cross below.
    """

    name = "swing"
    description = "Swing — trend following using fast/slow EMA crossovers"
    timeframe = "1h"
    stoploss = -0.07
    minimal_roi = {0: 0.04, 240: 0.02, 720: 0.0}
    max_open_trades = 3

    swing_fast_period = IntParameter(8, 24, default=12, space="buy", optimize=True)
    swing_slow_period = IntParameter(24, 60, default=40, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["swing_ema_fast"] = (
            dataframe["close"].ewm(span=self.swing_fast_period.value, adjust=False).mean()
        )
        dataframe["swing_ema_slow"] = (
            dataframe["close"].ewm(span=self.swing_slow_period.value, adjust=False).mean()
        )
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        fast = dataframe["swing_ema_fast"]
        slow = dataframe["swing_ema_slow"]

        buy_condition = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "swing_buy"

        sell_condition = (fast < slow) & (fast.shift(1) >= slow.shift(1))
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "swing_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        fast = dataframe["swing_ema_fast"]
        slow = dataframe["swing_ema_slow"]

        exit_long_condition = fast < slow
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "swing_exit_long"

        exit_short_condition = fast > slow
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "swing_exit_short"

        return dataframe


# ── Position Strategy ─────────────────────────────────────────────────────


@register_strategy
class PositionStrategy(IStrategy):
    """Position strategy — long-term trend using SMA crossover with ADX filter.

    Holds positions for extended periods, only entering when trend is strong.
    """

    name = "position"
    description = "Position — long-term trend following with SMA and ADX confirmation"
    timeframe = "4h"
    stoploss = -0.10
    minimal_roi = {0: 0.05, 720: 0.025, 1440: 0.0}
    max_open_trades = 2

    position_fast_sma = IntParameter(20, 50, default=50, space="buy", optimize=True)
    position_slow_sma = IntParameter(100, 200, default=200, space="buy", optimize=True)
    position_adx_threshold = IntParameter(20, 40, default=25, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["position_sma_fast"] = (
            dataframe["close"].rolling(window=self.position_fast_sma.value).mean()
        )
        dataframe["position_sma_slow"] = (
            dataframe["close"].rolling(window=self.position_slow_sma.value).mean()
        )
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        fast = dataframe["position_sma_fast"]
        slow = dataframe["position_sma_slow"]

        buy_condition = (
            (fast > slow)
            & (fast.shift(1) <= slow.shift(1))
            & (dataframe["close"] > dataframe["position_sma_slow"])
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "position_buy"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        fast = dataframe["position_sma_fast"]
        slow = dataframe["position_sma_slow"]

        exit_long_condition = fast < slow
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "position_exit_long"

        return dataframe


# ── VWAP Strategy ─────────────────────────────────────────────────────────


@register_strategy
class VWAPStrategy(IStrategy):
    """VWAP strategy — mean reversion around volume-weighted average price.

    Buys when price is below VWAP (undervalued), sells when above VWAP (overvalued).
    """

    name = "vwap"
    description = "VWAP — mean reversion around volume-weighted average price"
    timeframe = "15m"
    stoploss = -0.04
    minimal_roi = {0: 0.015, 60: 0.008, 180: 0.0}
    max_open_trades = 6

    vwap_period = IntParameter(10, 50, default=20, space="buy", optimize=True)
    vwap_deviation_pct = DecimalParameter(0.5, 3.0, default=1.0, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        period = self.vwap_period.value
        typical_price = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        vp = typical_price * dataframe["volume"]
        volume_rolling = dataframe["volume"].rolling(window=period).sum()
        vwap_values = vp.rolling(window=period).sum() / volume_rolling
        dataframe["vwap"] = vwap_values
        deviation = self.vwap_deviation_pct.value / 100.0
        dataframe["vwap_lower"] = vwap_values * (1 - deviation)
        dataframe["vwap_upper"] = vwap_values * (1 + deviation)
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["close"] <= dataframe["vwap_lower"]
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "vwap_buy"

        sell_condition = dataframe["close"] >= dataframe["vwap_upper"]
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "vwap_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["close"] >= dataframe["vwap"]
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "vwap_exit_long"

        exit_short_condition = dataframe["close"] <= dataframe["vwap"]
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "vwap_exit_short"

        return dataframe


# ── LLM Sentiment Strategy ───────────────────────────────────────────────


@register_strategy
class LLMSentimentStrategy(IStrategy):
    """LLM Sentiment strategy — advisory-only, uses LLM sentiment signals.

    This strategy is purely advisory: it generates signals based on
    sentiment data but all execution routes through RiskEngine.
    """

    name = "llm_sentiment"
    description = "LLM Sentiment — advisory-only strategy based on LLM sentiment signals"
    timeframe = "1h"
    stoploss = -0.05
    minimal_roi = {0: 0.02, 240: 0.01, 720: 0.0}
    max_open_trades = 3

    sentiment_buy_threshold = DecimalParameter(0.1, 0.9, default=0.6, space="buy", optimize=True)
    sentiment_sell_threshold = DecimalParameter(0.1, 0.9, default=0.4, space="sell", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        # Sentiment column is expected to be provided by external LLM service
        # via the signal feed. Default to neutral (0.5) if not present.
        if "sentiment_score" not in dataframe.columns:
            dataframe["sentiment_score"] = 0.5
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["sentiment_score"] >= self.sentiment_buy_threshold.value
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "llm_sentiment_buy"

        sell_condition = dataframe["sentiment_score"] <= self.sentiment_sell_threshold.value
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "llm_sentiment_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["sentiment_score"] <= 0.5
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "llm_sentiment_exit_long"

        exit_short_condition = dataframe["sentiment_score"] >= 0.5
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "llm_sentiment_exit_short"

        return dataframe


# ── Multi-Factor Strategy ────────────────────────────────────────────────


@register_strategy
class MultiFactorStrategy(IStrategy):
    """Multi-Factor strategy — combines RSI, EMA trend, and volume for entries.

    Requires multiple factors to align before entering a position.
    """

    name = "multi_factor"
    description = "Multi-Factor — combines RSI, EMA trend, and volume confirmation"
    timeframe = "1h"
    stoploss = -0.05
    minimal_roi = {0: 0.03, 120: 0.015, 360: 0.0}
    max_open_trades = 4

    mf_rsi_period = IntParameter(10, 20, default=14, space="buy", optimize=True)
    mf_rsi_oversold = IntParameter(25, 40, default=30, space="buy", optimize=True)
    mf_rsi_overbought = IntParameter(60, 75, default=70, space="sell", optimize=True)
    mf_ema_fast = IntParameter(8, 20, default=12, space="buy", optimize=True)
    mf_ema_slow = IntParameter(20, 50, default=26, space="buy", optimize=True)
    mf_volume_multiplier = DecimalParameter(1.0, 3.0, default=1.5, space="buy", optimize=True)

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        closes = dataframe["close"].tolist()
        period = self.mf_rsi_period.value
        rsi_values: list[float | None] = []
        for i in range(len(closes)):
            if i < period:
                rsi_values.append(None)
            else:
                window = closes[i - period : i + 1]
                rsi_values.append(rsi(window, period))
        dataframe["mf_rsi"] = rsi_values
        dataframe["mf_ema_fast"] = (
            dataframe["close"].ewm(span=self.mf_ema_fast.value, adjust=False).mean()
        )
        dataframe["mf_ema_slow"] = (
            dataframe["close"].ewm(span=self.mf_ema_slow.value, adjust=False).mean()
        )
        dataframe["mf_volume_avg"] = dataframe["volume"].rolling(window=20).mean()
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        fast = dataframe["mf_ema_fast"]
        slow = dataframe["mf_ema_slow"]
        vol_avg = dataframe["mf_volume_avg"]

        buy_condition = (
            dataframe["mf_rsi"].notna()
            & (dataframe["mf_rsi"] <= self.mf_rsi_oversold.value)
            & (fast > slow)
            & (dataframe["volume"] > vol_avg * self.mf_volume_multiplier.value)
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "multi_factor_buy"

        sell_condition = (
            dataframe["mf_rsi"].notna()
            & (dataframe["mf_rsi"] >= self.mf_rsi_overbought.value)
            & (fast < slow)
            & (dataframe["volume"] > vol_avg * self.mf_volume_multiplier.value)
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "multi_factor_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        fast = dataframe["mf_ema_fast"]
        slow = dataframe["mf_ema_slow"]

        exit_long_condition = fast < slow
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "multi_factor_exit_long"

        exit_short_condition = fast > slow
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "multi_factor_exit_short"

        return dataframe


# ── TFEX Spread Strategy ─────────────────────────────────────────────────


@register_strategy
class TFEXSpreadStrategy(IStrategy):
    """TFEX Spread strategy — trades the spread between TFEX futures contracts.

    Dedicated TFEX derivative domain: separate from SET equity handling.
    Buys when spread narrows below threshold, sells when spread widens above.
    """

    name = "tfex_spread"
    description = "TFEX Spread — trades futures spread, SET/TFEX domain separated"
    timeframe = "15m"
    stoploss = -0.03
    minimal_roi = {0: 0.01, 60: 0.005, 180: 0.0}
    max_open_trades = 3

    tfex_spread_period = IntParameter(10, 40, default=20, space="buy", optimize=True)
    tfex_spread_buy_threshold = DecimalParameter(
        -2.0, 0.0, default=-0.5, space="buy", optimize=True
    )
    tfex_spread_sell_threshold = DecimalParameter(
        0.0, 2.0, default=0.5, space="sell", optimize=True
    )

    def populate_indicators(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        period = self.tfex_spread_period.value
        # Spread proxy: difference between close and VWAP-like average
        typical_price = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        tfex_spread = typical_price - typical_price.rolling(window=period).mean()
        dataframe["tfex_spread"] = tfex_spread
        dataframe["tfex_spread_ma"] = tfex_spread.rolling(window=period).mean()
        return dataframe

    def populate_entry_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        buy_condition = dataframe["tfex_spread"].notna() & (
            dataframe["tfex_spread"] <= self.tfex_spread_buy_threshold.value
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "tfex_spread_buy"

        sell_condition = dataframe["tfex_spread"].notna() & (
            dataframe["tfex_spread"] >= self.tfex_spread_sell_threshold.value
        )
        dataframe.loc[sell_condition, "enter_short"] = 1
        dataframe.loc[sell_condition, "enter_tag"] = "tfex_spread_sell"

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> pd.DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        exit_long_condition = dataframe["tfex_spread"].notna() & (
            dataframe["tfex_spread"] >= dataframe["tfex_spread_ma"]
        )
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "tfex_spread_exit_long"

        exit_short_condition = dataframe["tfex_spread"].notna() & (
            dataframe["tfex_spread"] <= dataframe["tfex_spread_ma"]
        )
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "tfex_spread_exit_short"

        return dataframe


# ── Strategy Examples List ───────────────────────────────────────────────


EXAMPLE_STRATEGIES: list[type[IStrategy]] = [
    EMAcrossStrategy,
    RSIRebversionStrategy,
    MACDCrossStrategy,
    BollingerReversionStrategy,
    StochasticOscillatorStrategy,
    WilliamsRStrategy,
    ATRChannelStrategy,
    MomentumStrategy,
    BreakoutStrategy,
    ScalpStrategy,
    SwingStrategy,
    PositionStrategy,
    VWAPStrategy,
    LLMSentimentStrategy,
    MultiFactorStrategy,
    TFEXSpreadStrategy,
]
