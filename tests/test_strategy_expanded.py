from zksato.domain import SignalAction, StrategyConfig
from zksato.indicators import macd, rate_of_change, realized_volatility_pct
from zksato.strategy import StrategyEngine


def test_new_indicators_return_finite_values_when_history_is_sufficient() -> None:
    prices = [100 + (index * 0.5) + ((index % 5) * 0.1) for index in range(80)]
    macd_value = macd(prices)
    assert macd_value is not None
    assert len(macd_value) == 3
    roc = rate_of_change(prices, 10)
    volatility = realized_volatility_pct(prices, 20)
    assert roc is not None
    assert volatility is not None
    assert volatility >= 0


def test_expanded_strategy_catalog_evaluates_without_unknown_strategy() -> None:
    engine = StrategyEngine()
    prices = [100 + index * 0.2 for index in range(100)]
    names = [
        "ema_cross",
        "sma_cross",
        "rsi_reversion",
        "bollinger_reversion",
        "momentum",
        "macd_cross",
        "breakout",
    ]
    for name in names:
        config = StrategyConfig(name=name, min_history=20)
        signal = engine.evaluate("AOT", prices, config)
        assert signal.action in {SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD}
        assert 0 <= signal.confidence <= 1
        assert signal.strategy == name


def test_momentum_strategy_emits_directional_signals() -> None:
    engine = StrategyEngine()
    config = StrategyConfig(
        name="momentum",
        min_history=3,
        momentum_period=2,
        momentum_threshold_pct=0.5,
    )
    buy = engine.evaluate("AOT", [100.0, 100.2, 101.5], config)
    sell = engine.evaluate("AOT", [101.5, 100.5, 99.0], config)
    assert buy.action == SignalAction.BUY
    assert sell.action == SignalAction.SELL
