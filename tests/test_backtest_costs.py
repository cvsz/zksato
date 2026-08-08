from datetime import UTC, datetime, timedelta

from zksato.backtest import Backtester
from zksato.domain import BacktestRequest, Candle, StrategyConfig


def test_backtest_costs_reduce_equity() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    prices = [100, 99, 98, 97, 96, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104]
    candles = [
        Candle(
            timestamp=start + timedelta(days=index),
            open=price,
            high=price + 1,
            low=price - 1,
            close=price,
            volume=10_000,
        )
        for index, price in enumerate(prices)
    ]
    strategy = StrategyConfig(
        name="ema_cross",
        fast_period=2,
        slow_period=3,
        min_history=3,
    )
    no_cost = Backtester().run(
        BacktestRequest(
            symbol="AOT",
            candles=candles,
            strategy=strategy,
            commission_pct=0,
            slippage_pct=0,
        )
    )
    with_cost = Backtester().run(
        BacktestRequest(
            symbol="AOT",
            candles=candles,
            strategy=strategy,
            commission_pct=0.2,
            slippage_pct=0.2,
        )
    )
    assert with_cost.final_equity <= no_cost.final_equity
