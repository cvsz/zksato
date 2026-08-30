"""Tests for bot enhancements: confidence threshold, max_signals_per_tick,
new indicator strategies (stochastic, williams_r, atr_channel), and scalp bug fix."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from zksato.automation import AutomationEngine
from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import (
    BotConfig,
    Candle,
    Quote,
    SignalAction,
    StrategyConfig,
)
from zksato.indicators import stochastic_oscillator, williams_r
from zksato.service import TradingService
from zksato.store import StateStore
from zksato.strategy import StrategyEngine


def _build_candles(prices: list[float], base: datetime | None = None) -> list[Candle]:
    base = base or datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            timestamp=base + timedelta(minutes=i),
            open=p,
            high=p * 1.01,
            low=p * 0.99,
            close=p,
            volume=1000.0 + i * 10,
        )
        for i, p in enumerate(prices)
    ]


def _engine(
    confidence_threshold: float = 0.0,
    max_signals_per_tick: int = 0,
) -> tuple[AutomationEngine, StateStore, PaperBroker]:
    settings = Settings(trading_mode="paper", auth_required=False)
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000, match_resting_limits=False)
    service = TradingService(settings=settings, broker=broker, store=store)
    config = BotConfig(
        symbols=["AOT", "PTT"],
        confidence_threshold=confidence_threshold,
        max_signals_per_tick=max_signals_per_tick,
    )
    engine = AutomationEngine(settings=settings, store=store, service=service)
    engine.start(config)
    return engine, store, broker


# --- Scalp bug fix ---


def test_scalp_lower_band_destructuring_is_correct() -> None:
    """Regression: _scalp previously destructured lower as upper."""
    engine = StrategyEngine()
    prices = [100.0] * 20 + [95.0]  # price at lower end
    config = StrategyConfig(
        name="scalp",
        scalp_fast_period=3,
        scalp_slow_period=8,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config)
    # With correct lower-band destructuring, near_lower is True
    assert signal.action == SignalAction.SELL


# --- New indicators ---


def test_stochastic_oscillator_returns_k_and_d() -> None:
    candles = _build_candles([100.0 + i * 0.5 for i in range(20)])
    result = stochastic_oscillator(candles, k_period=14, d_period=3)
    assert result is not None
    k, d = result
    assert 0.0 <= k <= 100.0
    assert 0.0 <= d <= 100.0


def test_stochastic_oscillator_insufficient_history_returns_none() -> None:
    candles = _build_candles([100.0] * 5)
    result = stochastic_oscillator(candles, k_period=14, d_period=3)
    assert result is None


def test_williams_r_computes_value() -> None:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    flat_candles = [
        Candle(
            timestamp=base + timedelta(minutes=i),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=100.0,
        )
        for i in range(14)
    ]
    result = williams_r(flat_candles, period=14)
    # When high == low (zero range), expect None
    assert result is None


def test_williams_r_oversold() -> None:
    # falling prices: last close near the low
    prices = [100.0 - i * 0.5 for i in range(14)]
    candles = _build_candles(prices)
    result = williams_r(candles, period=14)
    assert result is not None
    assert result <= -50.0  # near lower range


def test_williams_r_overbought() -> None:
    # rising prices: last close near the high
    prices = [90.0 + i * 0.5 for i in range(14)]
    candles = _build_candles(prices)
    result = williams_r(candles, period=14)
    assert result is not None
    # Last close is highest → %R should be at or near 0
    assert result > -30.0


# --- New strategies ---


def test_stochastic_strategy_holds_without_candles() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.2 for i in range(20)]
    config = StrategyConfig(name="stochastic", min_history=10)
    signal = engine.evaluate("AOT", prices, config, candles=None)
    assert signal.action == SignalAction.HOLD
    assert "insufficient candle history" in signal.reason


def test_stochastic_strategy_evaluates_without_error() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.3 for i in range(30)]
    candles = _build_candles(prices)
    config = StrategyConfig(name="stochastic", stoch_k_period=14, stoch_d_period=3, min_history=10)
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action in {SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD}
    assert 0.0 <= signal.confidence <= 1.0


def test_stochastic_strategy_oversold_buy() -> None:
    engine = StrategyEngine()
    # Very low prices relative to range -> low stochastic values
    prices = [100.0] * 14 + [70.0, 68.0, 72.0]
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="stochastic",
        stoch_k_period=14,
        stoch_d_period=3,
        stoch_oversold=20.0,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    # Should be BUY or HOLD depending on D line – just ensure no crash and valid signal
    assert signal.action in {SignalAction.BUY, SignalAction.HOLD}


def test_williams_r_strategy_holds_without_candles() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.2 for i in range(20)]
    config = StrategyConfig(name="williams_r", min_history=10)
    signal = engine.evaluate("AOT", prices, config, candles=None)
    assert signal.action == SignalAction.HOLD
    assert "insufficient candle history" in signal.reason


def test_williams_r_strategy_oversold_produces_buy() -> None:
    engine = StrategyEngine()
    # Prices falling hard -> last price near period low -> WR near -100
    prices = [100.0 - i * 1.5 for i in range(20)]
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="williams_r",
        williams_r_period=14,
        williams_r_oversold=-80.0,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.BUY
    assert "oversold" in signal.reason


def test_williams_r_strategy_overbought_produces_sell() -> None:
    engine = StrategyEngine()
    # Prices rising hard -> last price near period high -> WR near 0
    prices = [80.0 + i * 1.5 for i in range(20)]
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="williams_r",
        williams_r_period=14,
        williams_r_overbought=-20.0,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.SELL
    assert "overbought" in signal.reason


def test_atr_channel_strategy_holds_without_candles() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.2 for i in range(30)]
    config = StrategyConfig(name="atr_channel", min_history=20)
    signal = engine.evaluate("AOT", prices, config, candles=None)
    assert signal.action == SignalAction.HOLD
    assert "insufficient candle history" in signal.reason


def test_atr_channel_strategy_buy_on_upward_breakout() -> None:
    engine = StrategyEngine()
    # Stable prices then sharp spike -> price > EMA + ATR*mult
    prices = [100.0] * 30 + [120.0]
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="atr_channel",
        slow_period=20,
        atr_period=14,
        atr_multiplier=1.0,
        min_history=20,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.BUY
    assert "broke above" in signal.reason


def test_atr_channel_strategy_sell_on_downward_breakout() -> None:
    engine = StrategyEngine()
    prices = [100.0] * 30 + [80.0]
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="atr_channel",
        slow_period=20,
        atr_period=14,
        atr_multiplier=1.0,
        min_history=20,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.SELL
    assert "broke below" in signal.reason


# --- Confidence threshold ---


@pytest.mark.asyncio
async def test_confidence_threshold_suppresses_low_confidence_signals() -> None:
    """Signals below confidence_threshold must be dropped before submission."""
    engine, store, _ = _engine(confidence_threshold=0.99)  # very high threshold
    # Seed enough prices for ema_cross but not enough to generate a confident signal
    prices = [100.0] * 30 + [100.1]
    for p in prices:
        store.update_quote(Quote(symbol="AOT", last=p))
        store.update_quote(Quote(symbol="PTT", last=p))
    await engine.tick()
    assert store.list_signals() == [] or all(s.confidence >= 0.99 for s in store.list_signals())


# --- max_signals_per_tick ---


@pytest.mark.asyncio
async def test_max_signals_per_tick_limits_execution() -> None:
    """At most max_signals_per_tick signals should be generated per tick call."""
    engine, store, _ = _engine(max_signals_per_tick=1)
    # Feed prices that will generate a signal for both symbols
    prices_aot = [100.0] * 24 + [115.0]
    prices_ptt = [50.0] * 24 + [60.0]
    for p in prices_aot:
        store.update_quote(Quote(symbol="AOT", last=p))
    for p in prices_ptt:
        store.update_quote(Quote(symbol="PTT", last=p))
    await engine.tick()
    assert len(store.list_signals()) <= 1


# --- BotConfig model validation ---


def test_bot_config_confidence_threshold_validates() -> None:
    config = BotConfig(symbols=["AOT"], confidence_threshold=0.75, max_signals_per_tick=5)
    assert config.confidence_threshold == 0.75
    assert config.max_signals_per_tick == 5


def test_bot_config_defaults_are_permissive() -> None:
    config = BotConfig(symbols=["AOT"])
    assert config.confidence_threshold == 0.0
    assert config.max_signals_per_tick == 0
