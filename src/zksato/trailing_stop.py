"""
Trailing stop loss mechanism.

Trailing stops dynamically adjust the stoploss price as the market moves
in favor of the position, locking in profits while giving the trade room
to breathe. Inspired by Freqtrade's trailing stop system.

All trailing stop logic is advisory — the actual stoploss order is
submitted through TradingService and evaluated by RiskEngine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from zksato.domain import Side

logger = logging.getLogger(__name__)


@dataclass
class TrailingStopState:
    """State of a trailing stop for a position."""

    symbol: str
    side: Side
    entry_price: float
    current_stop_price: float
    highest_price: float  # For long: highest price seen
    lowest_price: float  # For short: lowest price seen
    trailing_activated: bool = False
    activation_price: float | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TrailingStopManager:
    """Manages trailing stop losses for positions.

    Trailing stop logic:
    - For long positions: stop price trails the highest price seen
    - For short positions: stop price trails the lowest price seen
    - Trailing activates only after price moves favorably by
      trailing_stop_positive (relative to entry)
    - trailing_stop_positive_offset is the distance from the extreme
      price at which the stop is placed
    """

    def __init__(
        self,
        trailing_stop_positive: float | None = None,
        trailing_stop_positive_offset: float | None = None,
        trailing_only_offset_is_reached: bool = False,
    ) -> None:
        self.trailing_stop_positive = trailing_stop_positive
        self.trailing_stop_positive_offset = trailing_stop_positive_offset
        self.trailing_only_offset_is_reached = trailing_only_offset_is_reached
        self._states: dict[str, TrailingStopState] = {}

    def initialize(
        self,
        symbol: str,
        side: Side,
        entry_price: float,
    ) -> TrailingStopState:
        """Initialize trailing stop state for a new position."""
        state = TrailingStopState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            current_stop_price=entry_price,
            highest_price=entry_price,
            lowest_price=entry_price,
        )
        self._states[symbol] = state
        return state

    def update(
        self,
        symbol: str,
        current_price: float,
        current_time: datetime | None = None,
    ) -> TrailingStopState | None:
        """Update trailing stop state with new price.

        Returns the updated state, or None if no state exists for the symbol.
        """
        state = self._states.get(symbol)
        if state is None:
            return None

        current_time = current_time or datetime.now(UTC)

        if state.side == Side.BUY:
            # Long position: trail the highest price
            if current_price > state.highest_price:
                state.highest_price = current_price

                # Check if trailing should activate
                if not state.trailing_activated and self.trailing_stop_positive is not None:
                    profit_pct = (current_price - state.entry_price) / state.entry_price
                    if profit_pct >= self.trailing_stop_positive:
                        state.trailing_activated = True
                        state.activation_price = current_price
                        logger.info(
                            "Trailing stop activated for %s at %s (profit %.2f%%)",
                            symbol,
                            current_price,
                            profit_pct * 100,
                        )

                # If activated, adjust stop price
                if state.trailing_activated and self.trailing_stop_positive_offset is not None:
                    new_stop = state.highest_price * (1 - self.trailing_stop_positive_offset)
                    if new_stop > state.current_stop_price:
                        state.current_stop_price = new_stop
                        state.updated_at = current_time
        # Short position: trail the lowest price
        elif current_price < state.lowest_price:
            state.lowest_price = current_price

            # Check if trailing should activate
            if not state.trailing_activated and self.trailing_stop_positive is not None:
                profit_pct = (state.entry_price - current_price) / state.entry_price
                if profit_pct >= self.trailing_stop_positive:
                    state.trailing_activated = True
                    state.activation_price = current_price
                    logger.info(
                        "Trailing stop activated for %s at %s (profit %.2f%%)",
                        symbol,
                        current_price,
                        profit_pct * 100,
                    )

            # If activated, adjust stop price
            if state.trailing_activated and self.trailing_stop_positive_offset is not None:
                new_stop = state.lowest_price * (1 + self.trailing_stop_positive_offset)
                if new_stop < state.current_stop_price:
                    state.current_stop_price = new_stop
                    state.updated_at = current_time

        return state

    def get_stop_price(self, symbol: str) -> float | None:
        """Get the current stop price for a symbol."""
        state = self._states.get(symbol)
        return state.current_stop_price if state else None

    def is_triggered(
        self,
        symbol: str,
        current_price: float,
    ) -> bool:
        """Check if the trailing stop has been triggered."""
        state = self._states.get(symbol)
        if state is None or not state.trailing_activated:
            return False

        if state.side == Side.BUY:
            return current_price <= state.current_stop_price
        return current_price >= state.current_stop_price

    def remove(self, symbol: str) -> None:
        """Remove trailing stop state for a symbol (position closed)."""
        self._states.pop(symbol, None)

    def get_all_states(self) -> dict[str, TrailingStopState]:
        """Get all trailing stop states."""
        return dict(self._states)
