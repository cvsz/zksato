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
        dataframe["macd_signal"] = dataframe["macd_line"].ewm(
            span=self.buy_macd_signal.value, adjust=False
        ).mean()
        dataframe["macd_histogram"] = dataframe["macd_line"] - dataframe["macd_signal"]

        # MACD for sell side (same calculation, separate parameter set for hyperopt)
        dataframe["sell_macd_line"] = (
            dataframe["close"].ewm(span=self.sell_macd_fast.value, adjust=False).mean()
            - dataframe["close"].ewm(span=self.sell_macd_slow.value, adjust=False).mean()
        )
        dataframe["sell_macd_signal"] = dataframe["sell_macd_line"].ewm(
            span=self.sell_macd_signal.value, adjust=False
        ).mean()

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
        buy_condition = (
            (dataframe["macd_line"] > dataframe["macd_signal"])
            & (dataframe["macd_line"].shift(1) <= dataframe["macd_signal"].shift(1))
        )
        dataframe.loc[buy_condition, "enter_long"] = 1
        dataframe.loc[buy_condition, "enter_tag"] = "macd_cross_buy"

        # Sell: fast EMA crosses below slow EMA (MACD line crosses below signal)
        sell_condition = (
            (dataframe["macd_line"] < dataframe["macd_signal"])
            & (dataframe["macd_line"].shift(1) >= dataframe["macd_signal"].shift(1))
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
        exit_long_condition = (
            (dataframe["macd_line"] < dataframe["macd_signal"])
            & (dataframe["macd_line"].shift(1) >= dataframe["macd_signal"].shift(1))
        )
        dataframe.loc[exit_long_condition, "exit_long"] = 1
        dataframe.loc[exit_long_condition, "exit_tag"] = "macd_cross_exit_long"

        # Exit short: MACD line crosses above signal line
        exit_short_condition = (
            (dataframe["macd_line"] > dataframe["macd_signal"])
            & (dataframe["macd_line"].shift(1) <= dataframe["macd_signal"].shift(1))
        )
        dataframe.loc[exit_short_condition, "exit_short"] = 1
        dataframe.loc[exit_short_condition, "exit_tag"] = "macd_cross_exit_short"

        return dataframe


# ── Strategy Examples List ───────────────────────────────────────────────


EXAMPLE_STRATEGIES: list[type[IStrategy]] = [
    EMAcrossStrategy,
    RSIRebversionStrategy,
    MACDCrossStrategy,
]
