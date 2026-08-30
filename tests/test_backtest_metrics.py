from __future__ import annotations

from datetime import UTC, datetime, timedelta

from zksato.backtest import _annualized_sharpe, _annualized_sortino
from zksato.config import get_settings
from zksato.domain import BacktestRequest, Candle, StrategyConfig


def _candle(started: datetime, close: float) -> Candle:
    return Candle(
        timestamp=started,
        open=close,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=1000,
    )


def test_sharpe_ratio_positive_returns() -> None:
    returns = [0.01, 0.02, 0.015, 0.005, -0.005]
    sharpe = _annualized_sharpe(returns, 0.02)
    assert sharpe is not None
    assert sharpe > 0


def test_sortino_ratio_positive_returns() -> None:
    returns = [0.01, 0.02, 0.015, 0.005, -0.005]
    sortino = _annualized_sortino(returns, 0.02)
    assert sortino is not None
    assert sortino > 0


def test_calmar_ratio_positive_returns() -> None:
    from zksato.backtest import Backtester

    closes = [100.0, 105.0, 110.0, 108.0, 115.0]
    started = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [_candle(started + timedelta(days=i), c) for i, c in enumerate(closes)]
    request = BacktestRequest(
        symbol="AOT",
        candles=candles,
        strategy=StrategyConfig(name="ema_cross", fast_period=2, slow_period=3, min_history=3),
        initial_cash=100_000,
    )
    result = Backtester().run(request)
    if result.calmar_ratio is not None:
        assert result.calmar_ratio > 0


def test_sharpe_ratio_all_negative_returns() -> None:
    returns = [-0.01, -0.02, -0.015, -0.005, 0.005]
    sharpe = _annualized_sharpe(returns, 0.02)
    assert sharpe is not None
    assert sharpe < 0


def test_sortino_ratio_all_negative_returns() -> None:
    returns = [-0.01, -0.02, -0.015, -0.005, 0.005]
    sortino = _annualized_sortino(returns, 0.02)
    assert sortino is not None
    assert sortino < 0


def test_calmar_ratio_zero_drawdown() -> None:
    from zksato.backtest import Backtester

    closes = [100.0, 100.0, 100.0, 100.0, 100.0]
    started = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [_candle(started + timedelta(days=i), c) for i, c in enumerate(closes)]
    request = BacktestRequest(
        symbol="AOT",
        candles=candles,
        strategy=StrategyConfig(name="ema_cross", fast_period=2, slow_period=3, min_history=3),
        initial_cash=100_000,
    )
    result = Backtester().run(request)
    assert result.max_drawdown_pct == 0.0
    assert result.calmar_ratio is None


def test_metrics_with_empty_returns() -> None:
    assert _annualized_sharpe([], 0.02) is None
    assert _annualized_sortino([], 0.02) is None


def test_risk_free_rate_impacts_sharpe() -> None:
    returns = [0.01, 0.02, -0.01, 0.015, 0.005]
    settings = get_settings()
    original_rf = settings.risk_free_rate
    try:
        settings.risk_free_rate = 0.0
        sharpe_low = _annualized_sharpe(returns, settings.risk_free_rate)
        settings.risk_free_rate = 0.2
        sharpe_high = _annualized_sharpe(returns, settings.risk_free_rate)
        assert sharpe_low is not None
        assert sharpe_high is not None
        assert sharpe_low >= sharpe_high
    finally:
        settings.risk_free_rate = original_rf
