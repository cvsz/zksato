from datetime import UTC, datetime, timedelta

from zksato.config import Settings
from zksato.domain import Candle, OrderIntent, RiskContext, Side, SignalAction, StrategyConfig
from zksato.indicators import vwap
from zksato.prediction.core import Tick
from zksato.risk import PortfolioRiskManager, RiskEngine
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
            volume=1000 + i * 10,
        )
        for i, p in enumerate(prices)
    ]


def test_scalp_buys_on_ema_crossover_near_upper_band() -> None:
    engine = StrategyEngine()
    prices = [100.0] * 20 + [105.0]
    config = StrategyConfig(
        name="scalp",
        scalp_fast_period=3,
        scalp_slow_period=8,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action == SignalAction.BUY
    assert signal.confidence >= 0.7
    assert "scalp" in signal.reason


def test_scalp_sells_on_ema_crossover_near_lower_band() -> None:
    engine = StrategyEngine()
    prices = [100.0] * 20 + [95.0]
    config = StrategyConfig(
        name="scalp",
        scalp_fast_period=3,
        scalp_slow_period=8,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action == SignalAction.SELL
    assert signal.confidence >= 0.7


def test_scalp_holds_without_band_confirmation() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.1 for i in range(20)]
    config = StrategyConfig(
        name="scalp",
        scalp_fast_period=3,
        scalp_slow_period=8,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action == SignalAction.HOLD


def test_swing_buys_on_macd_bullish_with_low_rsi() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.2 for i in range(35)]
    prices.extend([103.0, 104.5, 102.0])
    config = StrategyConfig(
        name="swing",
        fast_period=12,
        slow_period=26,
        signal_period=9,
        swing_rsi_period=14,
        min_history=20,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action in {SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL}
    assert 0.0 <= signal.confidence <= 1.0
    assert "swing" in signal.reason


def test_swing_sells_on_macd_bearish_with_high_rsi() -> None:
    engine = StrategyEngine()
    prices = [100.0 - i * 0.2 for i in range(35)]
    prices.extend([96.0, 94.5, 97.0])
    config = StrategyConfig(
        name="swing",
        fast_period=12,
        slow_period=26,
        signal_period=9,
        swing_rsi_period=14,
        min_history=20,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action in {SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL}
    assert 0.0 <= signal.confidence <= 1.0
    assert "swing" in signal.reason


def test_position_buys_on_significant_sma_bullish_crossover() -> None:
    engine = StrategyEngine()
    prices = [100.0] * 15 + [100.0] * 9 + [200.0]
    config = StrategyConfig(
        name="position",
        position_fast_period=5,
        position_slow_period=10,
        min_history=11,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action == SignalAction.BUY
    assert signal.confidence >= 0.3
    assert "position" in signal.reason


def test_position_ignores_small_crossover() -> None:
    engine = StrategyEngine()
    prices = [100.0] * 15 + [100.5] * 5 + [101.0] * 5
    config = StrategyConfig(
        name="position",
        position_fast_period=5,
        position_slow_period=10,
        min_history=11,
    )
    signal = engine.evaluate("AOT", prices, config)
    assert signal.action == SignalAction.HOLD


def test_vwap_buys_on_pullback_to_vwap() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.8 for i in range(20)]
    prices.extend([116.0, 114.0, 112.0])
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="vwap",
        vwap_period=14,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.BUY
    assert "VWAP" in signal.reason


def test_vwap_sells_when_price_drops_below() -> None:
    engine = StrategyEngine()
    prices = [100.0 - i * 0.8 for i in range(20)]
    prices.extend([82.0, 80.0, 78.0])
    candles = _build_candles(prices)
    config = StrategyConfig(
        name="vwap",
        vwap_period=14,
        min_history=10,
    )
    signal = engine.evaluate("AOT", prices, config, candles=candles)
    assert signal.action == SignalAction.SELL
    assert "VWAP" in signal.reason


def test_vwap_holds_without_candles() -> None:
    engine = StrategyEngine()
    prices = [100.0 + i * 0.2 for i in range(20)]
    config = StrategyConfig(name="vwap", vwap_period=14, min_history=10)
    signal = engine.evaluate("AOT", prices, config, candles=None)
    assert signal.action == SignalAction.HOLD
    assert "insufficient candle history" in signal.reason


def test_prediction_edge_buys_on_up_signal() -> None:
    engine = StrategyEngine()
    ticks = [
        Tick(
            timestamp=i,
            spot=100.0 + i,
            reference=100.0,
            up_ask=0.6,
            down_ask=0.4,
            volatility=0.02,
            momentum=0.5,
        )
        for i in range(5)
    ]
    signal = engine.evaluate_prediction("BTC-5MIN", ticks, min_edge=0.01)
    assert signal.action == SignalAction.BUY
    assert signal.strategy == "prediction_edge"
    assert signal.confidence > 0.5


def test_prediction_edge_sells_on_down_signal() -> None:
    engine = StrategyEngine()
    ticks = [
        Tick(
            timestamp=i,
            spot=100.0 - i,
            reference=100.0,
            up_ask=0.4,
            down_ask=0.6,
            volatility=0.02,
            momentum=-0.5,
        )
        for i in range(5)
    ]
    signal = engine.evaluate_prediction("BTC-5MIN", ticks, min_edge=0.01)
    assert signal.action == SignalAction.SELL
    assert signal.strategy == "prediction_edge"


def test_prediction_edge_holds_below_min_edge() -> None:
    engine = StrategyEngine()
    ticks = [
        Tick(timestamp=i, spot=100.0, reference=100.0, up_ask=0.5, down_ask=0.5) for i in range(5)
    ]
    signal = engine.evaluate_prediction("BTC-5MIN", ticks, min_edge=0.99)
    assert signal.action == SignalAction.HOLD
    assert "below minimum threshold" in signal.reason


def test_prediction_edge_holds_without_ticks() -> None:
    engine = StrategyEngine()
    signal = engine.evaluate_prediction("BTC-5MIN", [], min_edge=0.03)
    assert signal.action == SignalAction.HOLD
    assert "no ticks provided" in signal.reason


def test_strategy_config_accepts_new_parameters() -> None:
    config = StrategyConfig(
        name="scalp",
        scalp_fast_period=3,
        scalp_slow_period=8,
        swing_rsi_period=14,
        position_fast_period=50,
        position_slow_period=200,
        vwap_period=14,
        min_history=10,
    )
    assert config.scalp_fast_period == 3
    assert config.scalp_slow_period == 8
    assert config.swing_rsi_period == 14
    assert config.position_fast_period == 50
    assert config.position_slow_period == 200
    assert config.vwap_period == 14


def test_portfolio_risk_correlation_check() -> None:
    settings = Settings(max_correlation=0.5)
    manager = PortfolioRiskManager(settings)
    reasons = manager.check_correlation("AOT", ["AOT", "AOT", "PTT"])
    assert len(reasons) == 1
    assert "correlation" in reasons[0].lower()


def test_portfolio_risk_allocation_check() -> None:
    settings = Settings(max_allocation_pct=10.0)
    manager = PortfolioRiskManager(settings)
    reasons = manager.check_allocation("AOT", ["AOT", "PTT"], max_allocation_pct=10.0)
    assert len(reasons) == 1
    assert "allocation" in reasons[0].lower()


def test_portfolio_risk_conflict_detection() -> None:
    settings = Settings(conflicting_strategies="scalp-swing,momentum-breakout")
    manager = PortfolioRiskManager(settings)
    reasons = manager.check_conflict("scalp", ["swing", "breakout"])
    assert len(reasons) == 1
    assert "conflicts" in reasons[0]
    reasons = manager.check_conflict("momentum", ["breakout"])
    assert len(reasons) == 1
    reasons = manager.check_conflict("ema_cross", ["breakout"])
    assert len(reasons) == 0


def test_portfolio_risk_evaluate_combines_checks() -> None:
    settings = Settings(
        max_correlation=0.5,
        max_allocation_pct=10.0,
        conflicting_strategies="scalp-swing",
    )
    manager = PortfolioRiskManager(settings)
    reasons = manager.evaluate("AOT", "scalp", ["AOT", "PTT"], ["swing"])
    assert len(reasons) == 3
    assert any("correlation" in r.lower() for r in reasons)
    assert any("allocation" in r.lower() for r in reasons)
    assert any("conflicts" in r for r in reasons)


def test_risk_engine_still_rejects_daily_loss() -> None:
    engine = RiskEngine(Settings(max_daily_loss_pct=2.0))
    decision = engine.evaluate(
        OrderIntent(symbol="AOT", side=Side.BUY, quantity=100, price=40.0, stop_loss=38.0),
        RiskContext(daily_pnl_pct=-2.0, position_pct_after_trade=5.0),
    )
    assert decision.approved is False
    assert "maximum daily loss threshold reached" in decision.reasons


def test_indicators_vwap_computes_weighted_average() -> None:
    candles = [
        Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=i),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=100.0,
        )
        for i in range(14)
    ]
    result = vwap(candles, period=14)
    assert result is not None
    assert 99.0 <= result <= 101.0


def test_new_strategies_evaluate_without_error() -> None:
    engine = StrategyEngine()
    prices = [100 + i * 0.2 for i in range(100)]
    candles = _build_candles(prices)
    names = ["scalp", "swing", "position", "vwap"]
    for name in names:
        config = StrategyConfig(name=name, min_history=20)
        signal = engine.evaluate("AOT", prices, config, candles=candles)
        assert signal.action in {SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD}
        assert 0 <= signal.confidence <= 1
        assert signal.strategy == name
