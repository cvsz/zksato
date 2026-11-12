"""Tests for trailing stop mechanism."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from zksato.domain import Side
from zksato.trailing_stop import TrailingStopManager, TrailingStopState


def _make_manager(
    trailing_stop_positive: float | None = 0.02,
    trailing_stop_positive_offset: float | None = 0.01,
    trailing_only_offset_is_reached: bool = False,
) -> TrailingStopManager:
    return TrailingStopManager(
        trailing_stop_positive=trailing_stop_positive,
        trailing_stop_positive_offset=trailing_stop_positive_offset,
        trailing_only_offset_is_reached=trailing_only_offset_is_reached,
    )


class TestTrailingStopState:
    def test_initial_state(self) -> None:
        state = TrailingStopState(
            symbol="AAPL",
            side=Side.BUY,
            entry_price=100.0,
            current_stop_price=100.0,
            highest_price=100.0,
            lowest_price=100.0,
        )
        assert state.symbol == "AAPL"
        assert state.side == Side.BUY
        assert state.entry_price == 100.0
        assert state.current_stop_price == 100.0
        assert state.highest_price == 100.0
        assert state.lowest_price == 100.0
        assert state.trailing_activated is False
        assert state.activation_price is None


class TestTrailingStopManagerInitialization:
    def test_initialize_long_position(self) -> None:
        manager = _make_manager()
        state = manager.initialize("AAPL", Side.BUY, 100.0)
        assert state.symbol == "AAPL"
        assert state.side == Side.BUY
        assert state.entry_price == 100.0
        assert state.current_stop_price == 100.0
        assert state.highest_price == 100.0
        assert state.lowest_price == 100.0
        assert state.trailing_activated is False

    def test_initialize_short_position(self) -> None:
        manager = _make_manager()
        state = manager.initialize("AAPL", Side.SELL, 100.0)
        assert state.side == Side.SELL
        assert state.entry_price == 100.0
        assert state.current_stop_price == 100.0

    def test_get_stop_price_returns_none_for_unknown_symbol(self) -> None:
        manager = _make_manager()
        assert manager.get_stop_price("UNKNOWN") is None

    def test_get_stop_price_returns_entry_price_initially(self) -> None:
        manager = _make_manager()
        manager.initialize("AAPL", Side.BUY, 100.0)
        assert manager.get_stop_price("AAPL") == 100.0


class TestTrailingStopLongPosition:
    def test_trails_highest_price(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        # Price moves up but not enough to activate trailing
        manager.update("AAPL", 101.0)  # 1% profit
        state = manager.get_all_states()["AAPL"]
        assert state.highest_price == 101.0
        assert state.trailing_activated is False
        assert state.current_stop_price == 100.0  # Still at entry

    def test_activates_trailing_when_profit_threshold_reached(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        # Price moves up 2% -> trailing activates
        manager.update("AAPL", 102.0)
        state = manager.get_all_states()["AAPL"]
        assert state.trailing_activated is True
        assert state.activation_price == 102.0
        # Stop should be at highest * (1 - offset) = 102 * 0.99 = 100.98
        assert state.current_stop_price == pytest.approx(100.98)

    def test_updates_stop_price_as_price_rises(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        manager.update("AAPL", 102.0)  # Activate
        assert manager.get_stop_price("AAPL") == pytest.approx(100.98)

        manager.update("AAPL", 105.0)  # New high
        assert manager.get_stop_price("AAPL") == pytest.approx(103.95)  # 105 * 0.99

        manager.update("AAPL", 110.0)  # New high
        assert manager.get_stop_price("AAPL") == pytest.approx(108.90)  # 110 * 0.99

    def test_stop_price_never_decreases_for_long(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        manager.update("AAPL", 105.0)
        stop_after_rise = manager.get_stop_price("AAPL")

        manager.update("AAPL", 103.0)  # Price drops
        stop_after_drop = manager.get_stop_price("AAPL")

        assert stop_after_drop == stop_after_rise  # Stop never moves down

    def test_is_triggered_when_price_falls_to_stop(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        manager.update("AAPL", 105.0)
        stop = manager.get_stop_price("AAPL")

        # Not triggered above stop
        assert manager.is_triggered("AAPL", stop + 1.0) is False

        # Triggered at stop
        assert manager.is_triggered("AAPL", stop) is True

        # Triggered below stop
        assert manager.is_triggered("AAPL", stop - 1.0) is True

    def test_not_triggered_before_activation(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        # Price drops before trailing activates
        manager.update("AAPL", 95.0)
        assert manager.is_triggered("AAPL", 95.0) is False


class TestTrailingStopShortPosition:
    def test_trails_lowest_price(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.SELL, 100.0)

        manager.update("AAPL", 99.0)  # 1% profit for short
        state = manager.get_all_states()["AAPL"]
        assert state.lowest_price == 99.0
        assert state.trailing_activated is False
        assert state.current_stop_price == 100.0

    def test_activates_trailing_when_profit_threshold_reached(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.SELL, 100.0)

        manager.update("AAPL", 98.0)  # 2% profit for short
        state = manager.get_all_states()["AAPL"]
        assert state.trailing_activated is True
        assert state.activation_price == 98.0
        # Stop at lowest * (1 + offset) = 98 * 1.01 = 98.98
        assert state.current_stop_price == pytest.approx(98.98)

    def test_updates_stop_price_as_price_falls(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.SELL, 100.0)

        manager.update("AAPL", 98.0)  # Activate
        assert manager.get_stop_price("AAPL") == pytest.approx(98.98)

        manager.update("AAPL", 95.0)  # New low
        assert manager.get_stop_price("AAPL") == pytest.approx(95.95)  # 95 * 1.01

    def test_stop_price_never_increases_for_short(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.SELL, 100.0)

        manager.update("AAPL", 95.0)
        stop_after_fall = manager.get_stop_price("AAPL")

        manager.update("AAPL", 97.0)  # Price rises
        stop_after_rise = manager.get_stop_price("AAPL")

        assert stop_after_rise == stop_after_fall  # Stop never moves up

    def test_is_triggered_when_price_rises_to_stop(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.SELL, 100.0)

        manager.update("AAPL", 95.0)
        stop = manager.get_stop_price("AAPL")

        assert manager.is_triggered("AAPL", stop - 1.0) is False
        assert manager.is_triggered("AAPL", stop) is True
        assert manager.is_triggered("AAPL", stop + 1.0) is True


class TestTrailingStopConfiguration:
    def test_no_trailing_when_positive_none(self) -> None:
        manager = _make_manager(trailing_stop_positive=None, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)

        manager.update("AAPL", 150.0)
        state = manager.get_all_states()["AAPL"]
        assert state.trailing_activated is False
        assert state.current_stop_price == 100.0

    def test_no_trailing_when_offset_none(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=None)
        manager.initialize("AAPL", Side.BUY, 100.0)

        manager.update("AAPL", 105.0)
        state = manager.get_all_states()["AAPL"]
        assert state.trailing_activated is True
        assert state.current_stop_price == 100.0  # Stop not adjusted without offset

    def test_trailing_only_offset_is_reached(self) -> None:
        manager = _make_manager(
            trailing_stop_positive=0.02,
            trailing_stop_positive_offset=0.01,
            trailing_only_offset_is_reached=True,
        )
        manager.initialize("AAPL", Side.BUY, 100.0)

        # Price moves to activation level (2%)
        manager.update("AAPL", 102.0)
        state = manager.get_all_states()["AAPL"]
        # Note: trailing_only_offset_is_reached is stored but not yet implemented in update logic
        # Current behavior: trailing activates and stop is set immediately
        assert state.trailing_activated is True
        assert state.current_stop_price == pytest.approx(100.98)


class TestTrailingStopManagerOperations:
    def test_remove_state(self) -> None:
        manager = _make_manager()
        manager.initialize("AAPL", Side.BUY, 100.0)
        assert manager.get_stop_price("AAPL") == 100.0

        manager.remove("AAPL")
        assert manager.get_stop_price("AAPL") is None

    def test_get_all_states(self) -> None:
        manager = _make_manager()
        manager.initialize("AAPL", Side.BUY, 100.0)
        manager.initialize("GOOG", Side.SELL, 200.0)

        states = manager.get_all_states()
        assert "AAPL" in states
        assert "GOOG" in states
        assert states["AAPL"].side == Side.BUY
        assert states["GOOG"].side == Side.SELL

    def test_update_returns_none_for_unknown_symbol(self) -> None:
        manager = _make_manager()
        result = manager.update("UNKNOWN", 100.0)
        assert result is None

    def test_update_uses_current_time_when_not_provided(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)
        # Update with price that triggers trailing activation and stop change
        before = datetime.now(UTC)
        state = manager.update("AAPL", 105.0)
        after = datetime.now(UTC)
        # updated_at should be set when stop price changes
        assert before <= state.updated_at <= after

    def test_update_uses_provided_time(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)
        custom_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        # Price change that triggers stop price update
        state = manager.update("AAPL", 105.0, current_time=custom_time)
        assert state.updated_at == custom_time


class TestTrailingStopEdgeCases:
    def test_multiple_symbols_independent(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)
        manager.initialize("GOOG", Side.BUY, 200.0)

        manager.update("AAPL", 105.0)
        manager.update("GOOG", 190.0)  # GOOG drops

        assert manager.get_stop_price("AAPL") == pytest.approx(103.95)
        assert manager.get_stop_price("GOOG") == 200.0  # No trailing for GOOG

    def test_reinitialize_same_symbol_replaces_state(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.02, trailing_stop_positive_offset=0.01)
        manager.initialize("AAPL", Side.BUY, 100.0)
        manager.update("AAPL", 105.0)
        assert manager.get_stop_price("AAPL") == pytest.approx(103.95)

        # Reinitialize with new entry price
        manager.initialize("AAPL", Side.BUY, 120.0)
        assert manager.get_stop_price("AAPL") == 120.0

    def test_short_profit_calculation(self) -> None:
        manager = _make_manager(trailing_stop_positive=0.05, trailing_stop_positive_offset=0.02)
        manager.initialize("AAPL", Side.SELL, 100.0)

        # 5% profit for short = price drops to 95
        manager.update("AAPL", 95.0)
        state = manager.get_all_states()["AAPL"]
        assert state.trailing_activated is True
        # Stop = 95 * 1.02 = 96.9
        assert state.current_stop_price == pytest.approx(96.9)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])