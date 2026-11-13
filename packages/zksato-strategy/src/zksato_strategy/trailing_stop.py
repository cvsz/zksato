"""Trailing stop management for position protection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TrailingStopType(Enum):
    """Types of trailing stops."""

    PERCENTAGE = "percentage"
    ATR = "atr"
    FIXED = "fixed"


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop."""

    stop_type: TrailingStopType = TrailingStopType.PERCENTAGE
    percentage: float = 0.02  # 2%
    atr_multiplier: float = 2.0
    atr_period: int = 14
    fixed_amount: float = 0.0
    activation_price: float | None = None  # Price at which trailing activates


@dataclass
class TrailingStopState:
    """Current state of a trailing stop."""

    symbol: str
    config: TrailingStopConfig
    highest_price: float = 0.0  # For long positions
    lowest_price: float = 0.0  # For short positions
    stop_price: float = 0.0
    activated: bool = False
    side: str = "long"  # "long" or "short"


class TrailingStop:
    """Manages trailing stops for positions."""

    def __init__(self) -> None:
        self._stops: dict[str, TrailingStopState] = {}

    def create_stop(
        self,
        symbol: str,
        entry_price: float,
        side: str,
        config: TrailingStopConfig | None = None,
    ) -> TrailingStopState:
        """Create a new trailing stop."""
        if config is None:
            config = TrailingStopConfig()

        state = TrailingStopState(
            symbol=symbol,
            config=config,
            side=side.lower(),
        )

        if side.lower() == "long":
            state.highest_price = entry_price
            state.stop_price = self._calculate_stop_price(entry_price, config, "long")
        else:
            state.lowest_price = entry_price
            state.stop_price = self._calculate_stop_price(entry_price, config, "short")

        # Check activation
        if config.activation_price is not None:
            if (side.lower() == "long" and entry_price >= config.activation_price) or (
                side.lower() == "short" and entry_price <= config.activation_price
            ):
                state.activated = True
        else:
            state.activated = True

        self._stops[symbol] = state
        return state

    def update(
        self, symbol: str, current_price: float, atr_value: float | None = None
    ) -> TrailingStopState | None:
        """Update trailing stop with current price."""
        if symbol not in self._stops:
            return None

        state = self._stops[symbol]
        config = state.config

        if state.side == "long":
            if current_price > state.highest_price:
                state.highest_price = current_price
                if state.activated:
                    state.stop_price = self._calculate_stop_price(
                        current_price, config, "long", atr_value
                    )
            elif (
                config.activation_price
                and not state.activated
                and current_price >= config.activation_price
            ):
                state.activated = True
                state.stop_price = self._calculate_stop_price(
                    current_price, config, "long", atr_value
                )

        elif current_price < state.lowest_price:
            state.lowest_price = current_price
            if state.activated:
                state.stop_price = self._calculate_stop_price(
                    current_price, config, "short", atr_value
                )
        elif (
            config.activation_price
            and not state.activated
            and current_price <= config.activation_price
        ):
            state.activated = True
            state.stop_price = self._calculate_stop_price(current_price, config, "short", atr_value)

        return state

    def check_stop(self, symbol: str, current_price: float) -> bool:
        """Check if stop is hit."""
        if symbol not in self._stops:
            return False

        state = self._stops[symbol]

        if state.side == "long":
            return current_price <= state.stop_price
        else:
            return current_price >= state.stop_price

    def get_stop_price(self, symbol: str) -> float | None:
        """Get current stop price."""
        if symbol not in self._stops:
            return None
        return self._stops[symbol].stop_price

    def remove_stop(self, symbol: str) -> bool:
        """Remove a trailing stop."""
        if symbol in self._stops:
            del self._stops[symbol]
            return True
        return False

    def get_all_stops(self) -> dict[str, TrailingStopState]:
        """Get all trailing stops."""
        return self._stops.copy()

    def _calculate_stop_price(
        self,
        reference_price: float,
        config: TrailingStopConfig,
        side: str,
        atr_value: float | None = None,
    ) -> float:
        """Calculate stop price based on config."""
        if config.stop_type == TrailingStopType.PERCENTAGE:
            if side == "long":
                return reference_price * (1 - config.percentage)
            else:
                return reference_price * (1 + config.percentage)

        elif config.stop_type == TrailingStopType.ATR:
            if atr_value is None:
                atr_value = reference_price * 0.01  # Fallback to 1%
            if side == "long":
                return reference_price - (config.atr_multiplier * atr_value)
            else:
                return reference_price + (config.atr_multiplier * atr_value)

        elif config.stop_type == TrailingStopType.FIXED:
            if side == "long":
                return reference_price - config.fixed_amount
            else:
                return reference_price + config.fixed_amount

        return reference_price
