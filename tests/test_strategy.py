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
