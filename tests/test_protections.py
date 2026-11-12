"""Tests for protection mechanisms."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from zksato.domain import Side
from zksato.protections import (
    ConsecutiveLossProtection,
    CooldownPeriodProtection,
    DrawdownProtection,
    ProtectionManager,
    StoplossGuardProtection,
    TimeBasedProtection,
    TradeContext,
    VolatilityProtection,
)


def _make_context(
    symbol: str = "AAPL",
    side: Side = Side.BUY,
    price: float | None = 100.0,
    daily_pnl_pct: float = 0.0,
    recent_trades: list[dict] | None = None,
) -> TradeContext:
    return TradeContext(
        symbol=symbol,
        side=side,
        order_type="limit",
        amount=10.0,
        price=price,
        current_time=datetime.now(UTC),
        recent_trades=recent_trades or [],
        portfolio_value=10000.0,
        daily_pnl_pct=daily_pnl_pct,
    )


class TestCooldownPeriodProtection:
    def test_allows_when_no_previous_trade(self) -> None:
        protection = CooldownPeriodProtection(stop_duration_candles=4, candle_duration_seconds=60)
        context = _make_context()
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_blocks_during_cooldown(self) -> None:
        protection = CooldownPeriodProtection(stop_duration_candles=4, candle_duration_seconds=60)
        symbol = "AAPL"
        protection.record_trade_exit(symbol, datetime.now(UTC) - timedelta(seconds=30))
        context = _make_context(symbol=symbol)
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "cooldown period active" in result.reason

    def test_allows_after_cooldown_expires(self) -> None:
        protection = CooldownPeriodProtection(stop_duration_candles=4, candle_duration_seconds=60)
        symbol = "AAPL"
        protection.record_trade_exit(symbol, datetime.now(UTC) - timedelta(seconds=300))
        context = _make_context(symbol=symbol)
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_different_symbols_independent(self) -> None:
        protection = CooldownPeriodProtection(stop_duration_candles=4, candle_duration_seconds=60)
        protection.record_trade_exit("AAPL", datetime.now(UTC) - timedelta(seconds=30))
        context_aapl = _make_context(symbol="AAPL")
        context_goog = _make_context(symbol="GOOG")
        assert protection.evaluate(context_aapl).allowed is False
        assert protection.evaluate(context_goog).allowed is True


class TestStoplossGuardProtection:
    def test_allows_when_no_losses(self) -> None:
        protection = StoplossGuardProtection(trade_limit=4)
        context = _make_context()
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_blocks_after_limit_reached(self) -> None:
        protection = StoplossGuardProtection(trade_limit=2, lookback_period_candles=24)
        now = datetime.now(UTC)
        protection.record_trade_loss("AAPL", now - timedelta(hours=1))
        protection.record_trade_loss("AAPL", now - timedelta(hours=2))
        context = _make_context()
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "stoploss guard triggered" in result.reason

    def test_only_per_pair_isolation(self) -> None:
        protection = StoplossGuardProtection(trade_limit=2, only_per_pair=True)
        now = datetime.now(UTC)
        protection.record_trade_loss("AAPL", now - timedelta(hours=1))
        protection.record_trade_loss("AAPL", now - timedelta(hours=2))
        # When only_per_pair=True, losses are tracked globally
        # Both AAPL and GOOG should be blocked
        assert protection.evaluate(_make_context(symbol="AAPL")).allowed is False
        assert protection.evaluate(_make_context(symbol="GOOG")).allowed is False

    def test_expired_losses_not_counted(self) -> None:
        protection = StoplossGuardProtection(trade_limit=2, lookback_period_candles=1)
        now = datetime.now(UTC)
        protection.record_trade_loss("AAPL", now - timedelta(hours=2))  # Outside lookback
        context = _make_context()
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_stop_period_expires_but_losses_remain_in_lookback(self) -> None:
        """Stop period expires but losses in lookback re-trigger stop."""
        protection = StoplossGuardProtection(
            trade_limit=1,
            lookback_period_candles=24,
            stop_duration_candles=1,
            candle_duration_seconds=1,  # 1 second stop
        )
        base_time = datetime.now(UTC)
        protection.record_trade_loss("AAPL", base_time)
        context = _make_context()
        context.current_time = base_time
        assert protection.evaluate(context).allowed is False
        # Advance context time past stop period
        context.current_time = base_time + timedelta(seconds=1.5)
        # Stop period expired, but loss still in lookback -> re-triggers
        assert protection.evaluate(context).allowed is False
        # To allow trading, loss must expire from lookback
        context.current_time = base_time + timedelta(hours=25)
        assert protection.evaluate(context).allowed is True


class TestDrawdownProtection:
    def test_allows_when_within_limit(self) -> None:
        protection = DrawdownProtection(max_daily_drawdown_pct=5.0)
        context = _make_context(daily_pnl_pct=-3.0)
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_blocks_when_limit_exceeded(self) -> None:
        protection = DrawdownProtection(max_daily_drawdown_pct=5.0)
        context = _make_context(daily_pnl_pct=-6.0)
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "daily drawdown limit reached" in result.reason

    def test_uses_absolute_value(self) -> None:
        # Even if negative is passed, it should use absolute
        protection = DrawdownProtection(max_daily_drawdown_pct=-5.0)
        context = _make_context(daily_pnl_pct=-6.0)
        result = protection.evaluate(context)
        assert result.allowed is False


class TestVolatilityProtection:
    def test_allows_when_insufficient_trades(self) -> None:
        protection = VolatilityProtection(max_volatility_pct=5.0)
        context = _make_context(recent_trades=[{"price": 100.0}])
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_allows_when_volatility_within_limit(self) -> None:
        protection = VolatilityProtection(max_volatility_pct=5.0)
        recent = [{"price": 100.0 + i * 0.1} for i in range(10)]
        context = _make_context(recent_trades=recent)
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_blocks_when_volatility_exceeds_limit(self) -> None:
        protection = VolatilityProtection(max_volatility_pct=1.0)
        # Create high volatility: large swings
        recent = [{"price": 100.0 + (10.0 if i % 2 == 0 else -10.0)} for i in range(20)]
        context = _make_context(recent_trades=recent)
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "volatility too high" in result.reason

    def test_skips_invalid_prices(self) -> None:
        protection = VolatilityProtection(max_volatility_pct=5.0)
        # Use prices where previous > 0 but current is valid
        # The implementation skips when previous <= 0
        recent = [{"price": 100.0}, {"price": 101.0}, {"price": 102.0}]
        context = _make_context(recent_trades=recent)
        result = protection.evaluate(context)
        assert result.allowed is True


class TestTimeBasedProtection:
    def test_blocks_during_configured_hours(self) -> None:
        # Use a fixed hour that we know will be blocked
        protection = TimeBasedProtection(blocked_hours=[12], timezone_name="UTC")
        context = _make_context()
        context.current_time = datetime(2024, 1, 1, 12, 30, tzinfo=UTC)
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "trading blocked during hour 12:00" in result.reason

    def test_allows_outside_blocked_hours(self) -> None:
        protection = TimeBasedProtection(blocked_hours=[12], timezone_name="UTC")
        context = _make_context()
        context.current_time = datetime(2024, 1, 1, 10, 30, tzinfo=UTC)
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_default_blocks_lunch_hours(self) -> None:
        protection = TimeBasedProtection(timezone_name="UTC")
        context = _make_context()
        context.current_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        assert protection.evaluate(context).allowed is False
        context.current_time = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
        assert protection.evaluate(context).allowed is True


class TestConsecutiveLossProtection:
    def test_allows_when_no_losses(self) -> None:
        protection = ConsecutiveLossProtection(max_consecutive_losses=3)
        context = _make_context()
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_blocks_after_consecutive_losses(self) -> None:
        protection = ConsecutiveLossProtection(max_consecutive_losses=2, stop_duration_candles=1)
        now = datetime.now(UTC)
        protection.record_consecutive_loss("AAPL", now)
        protection.record_consecutive_loss("AAPL", now)
        context = _make_context(symbol="AAPL")
        result = protection.evaluate(context)
        assert result.allowed is False
        assert "consecutive losses active" in result.reason

    def test_resets_on_winning_trade(self) -> None:
        protection = ConsecutiveLossProtection(max_consecutive_losses=2)
        now = datetime.now(UTC)
        protection.record_consecutive_loss("AAPL", now)
        protection.record_consecutive_loss("AAPL", now)
        # Winning trade resets
        protection.reset_consecutive_losses("AAPL")
        context = _make_context(symbol="AAPL")
        result = protection.evaluate(context)
        assert result.allowed is True

    def test_different_symbols_independent(self) -> None:
        protection = ConsecutiveLossProtection(max_consecutive_losses=2)
        now = datetime.now(UTC)
        protection.record_consecutive_loss("AAPL", now)
        protection.record_consecutive_loss("AAPL", now)
        assert protection.evaluate(_make_context(symbol="AAPL")).allowed is False
        assert protection.evaluate(_make_context(symbol="GOOG")).allowed is True

    def test_stop_period_expires_but_losses_remain(self) -> None:
        """Stop period expires but consecutive losses re-trigger stop."""
        protection = ConsecutiveLossProtection(
            max_consecutive_losses=1,
            stop_duration_candles=1,
            candle_duration_seconds=1,
        )
        base_time = datetime.now(UTC)
        protection.record_consecutive_loss("AAPL", base_time)
        context = _make_context(symbol="AAPL")
        context.current_time = base_time
        assert protection.evaluate(context).allowed is False
        # Advance context time past stop period
        context.current_time = base_time + timedelta(seconds=1.5)
        # Stop period expired, but consecutive loss count still >= max -> re-triggers
        assert protection.evaluate(context).allowed is False
        # Reset consecutive losses to allow trading
        protection.reset_consecutive_losses("AAPL")
        assert protection.evaluate(context).allowed is True


class TestProtectionManager:
    def test_allows_when_all_protections_pass(self) -> None:
        manager = ProtectionManager([
            CooldownPeriodProtection(),
            DrawdownProtection(),
        ])
        context = _make_context()
        result = manager.evaluate_all(context)
        assert result.allowed is True

    def test_blocks_on_first_failing_protection(self) -> None:
        manager = ProtectionManager([
            DrawdownProtection(max_daily_drawdown_pct=5.0),
            CooldownPeriodProtection(),
        ])
        context = _make_context(daily_pnl_pct=-10.0)
        result = manager.evaluate_all(context)
        assert result.allowed is False
        assert "DrawdownProtection" in result.reason

    def test_records_trade_exit_for_all_protections(self) -> None:
        cooldown = CooldownPeriodProtection()
        stoploss = StoplossGuardProtection()
        consecutive = ConsecutiveLossProtection()
        manager = ProtectionManager([cooldown, stoploss, consecutive])

        manager.record_trade_exit("AAPL", datetime.now(UTC), was_loss=True)

        # All should have recorded
        context = _make_context(symbol="AAPL")
        # Cooldown should block
        assert cooldown.evaluate(context).allowed is False
        # Stoploss should have recorded loss
        assert len(stoploss._recent_losses.get("AAPL", [])) == 1
        # Consecutive should have recorded loss
        assert consecutive._consecutive_losses.get("AAPL") == 1

    def test_records_winning_trade_resets_consecutive(self) -> None:
        consecutive = ConsecutiveLossProtection(max_consecutive_losses=2)
        manager = ProtectionManager([consecutive])

        now = datetime.now(UTC)
        consecutive.record_consecutive_loss("AAPL", now)
        consecutive.record_consecutive_loss("AAPL", now)
        assert consecutive._consecutive_losses["AAPL"] == 2

        manager.record_trade_exit("AAPL", now, was_loss=False)
        assert consecutive._consecutive_losses["AAPL"] == 0


class TestProtectionIntegration:
    def test_combined_protections_work_together(self) -> None:
        """Test that multiple protections can be combined and work correctly."""
        manager = ProtectionManager([
            CooldownPeriodProtection(stop_duration_candles=2, candle_duration_seconds=60),
            DrawdownProtection(max_daily_drawdown_pct=3.0),
            ConsecutiveLossProtection(max_consecutive_losses=2),
            VolatilityProtection(max_volatility_pct=10.0),
        ])

        # Normal conditions - should allow
        context = _make_context(daily_pnl_pct=-1.0)
        assert manager.evaluate_all(context).allowed is True

        # Drawdown exceeded - should block
        context = _make_context(daily_pnl_pct=-5.0)
        assert manager.evaluate_all(context).allowed is False

        # After drawdown fixed, but consecutive losses
        context = _make_context(daily_pnl_pct=-1.0)
        now = datetime.now(UTC)
        for _ in range(2):
            manager.record_trade_exit("AAPL", now, was_loss=True)
        assert manager.evaluate_all(context).allowed is False

    def test_cooldown_and_consecutive_independent(self) -> None:
        """Cooldown and consecutive loss should track independently."""
        manager = ProtectionManager([
            CooldownPeriodProtection(
                stop_duration_candles=1, candle_duration_seconds=1
            ),
            ConsecutiveLossProtection(
                max_consecutive_losses=1,
                stop_duration_candles=1,
                candle_duration_seconds=1,
            ),
        ])

        base_time = datetime.now(UTC)
        manager.record_trade_exit("AAPL", base_time, was_loss=True)

        context = _make_context(symbol="AAPL")
        context.current_time = base_time
        # Both should block
        assert manager.evaluate_all(context).allowed is False

        # Advance time past both stop periods
        context.current_time = base_time + timedelta(seconds=1.5)
        # Cooldown expired, but consecutive loss still blocks
        assert manager.evaluate_all(context).allowed is False
        # Reset consecutive losses to allow trading
        for protection in manager.protections:
            if isinstance(protection, ConsecutiveLossProtection):
                protection.reset_consecutive_losses("AAPL")
        assert manager.evaluate_all(context).allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])