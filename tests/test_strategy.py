from datetime import UTC, datetime, timedelta

from zksato.backtest import Backtester
from zksato.domain import BacktestRequest, Candle, SignalAction, StrategyConfig
from zksato.strategy import StrategyEngine


def test_ema_strategy_generates_signal_object() -> None:
    engine = StrategyEngine()
    prices: list[float] = [10.0, 10.0, 10.0, 9.0, 9.0, 9.0, 12.0]
    signal = engine.evaluate(
        "AOT",
        prices,
        StrategyConfig(name="ema_cross", fast_period=2, slow_period=4, min_history=5),
    )
    assert signal.symbol == "AOT"
    assert signal.action in {SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL}


def test_breakout_detects_new_high() -> None:
    engine = StrategyEngine()
    signal = engine.evaluate(
        "PTT",
        [10, 10.2, 10.1, 10.3, 11.0],
        StrategyConfig(name="breakout", breakout_period=4, min_history=5),
    )
    assert signal.action == SignalAction.BUY


def test_backtest_returns_metrics() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [10, 10.1, 9.9, 10.2, 10.4, 10.7, 10.5, 10.9, 11.2, 11.0]
    candles = [
        Candle(
            timestamp=start + timedelta(days=index),
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=10_000,
        )
        for index, price in enumerate(closes)
    ]
    result = Backtester().run(
        BacktestRequest(
            symbol="AOT",
            candles=candles,
            strategy=StrategyConfig(
                name="breakout",
                breakout_period=3,
                min_history=4,
            ),
            initial_cash=100_000,
            order_size=100,
        )
    )
    assert result.symbol == "AOT"
    assert result.final_equity > 0
    assert len(result.equity_curve) == len(candles)


def test_stat_arb_strategy() -> None:
    engine = StrategyEngine()
    # Baseline steady prices around 100.0, then an oversold dump
    prices_oversold = [100.0] * 25 + [80.0]
    config = StrategyConfig(
        name="stat_arb",
        stat_arb_period=20,
        stat_arb_zscore_entry=2.0,
        min_history=20,
    )
    sig_buy = engine.evaluate("DELTA", prices_oversold, config)
    assert sig_buy.action == SignalAction.BUY
    assert "oversold" in sig_buy.reason

    # Overbought spike
    prices_overbought = [100.0] * 25 + [120.0]
    sig_sell = engine.evaluate("DELTA", prices_overbought, config)
    assert sig_sell.action == SignalAction.SELL
    assert "overbought" in sig_sell.reason

    # Neutral inside bounds
    prices_neutral = [100.0, 100.1, 99.9, 100.2] * 7
    sig_hold = engine.evaluate("DELTA", prices_neutral, config)
    assert sig_hold.action == SignalAction.HOLD


def test_tfex_spread_strategy() -> None:
    engine = StrategyEngine()
    # Steady baseline around 950.0, then a sharp basis drop
    prices = [950.0] * 30
    config = StrategyConfig(
        name="tfex_spread",
        fast_period=5,
        tfex_spread_threshold=3.0,
        min_history=20,
    )
    # Basis dump: price drops 10 pts below steady EMA
    sig_buy = engine.evaluate("S50M26", prices + [940.0], config)
    assert sig_buy.action == SignalAction.BUY
    assert "discount" in sig_buy.reason

    # Basis surge: price spikes 10 pts above steady EMA
    sig_sell = engine.evaluate("S50M26", prices + [960.0], config)
    assert sig_sell.action == SignalAction.SELL
    assert "premium" in sig_sell.reason
