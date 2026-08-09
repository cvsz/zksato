from datetime import UTC, datetime, timedelta

from zksato.backtest import Backtester
from zksato.domain import BacktestRequest, Candle, StrategyConfig


def test_backtest_reports_cost_exposure_and_benchmark_analytics() -> None:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    closes = [100.0, 100.5, 101.5, 102.0, 100.0, 99.0, 100.5, 102.0, 99.5, 98.5]
    candles = [
        Candle(
            timestamp=started + timedelta(minutes=index),
            open=price,
            high=price + 0.5,
            low=price - 0.5,
            close=price,
            volume=1000,
        )
        for index, price in enumerate(closes)
    ]
    result = Backtester().run(
        BacktestRequest(
            symbol="AOT",
            candles=candles,
            strategy=StrategyConfig(
                name="momentum",
                min_history=3,
                momentum_period=1,
                momentum_threshold_pct=0.1,
            ),
            initial_cash=100_000,
            order_size=100,
            commission_pct=0.15,
            slippage_pct=0.05,
        )
    )
    assert 0 <= result.exposure_pct <= 100
    assert result.fees_paid >= 0
    assert result.closed_trades >= 1
    assert result.total_trades >= result.closed_trades * 2
    assert result.buy_and_hold_return_pct == (closes[-1] - closes[0]) / closes[0] * 100
    assert result.gross_profit >= 0
    assert result.gross_loss >= 0
