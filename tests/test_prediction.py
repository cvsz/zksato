from datetime import UTC, datetime

import pytest

from zksato.broker.prediction import PredictionBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderStatus, OrderType, Side
from zksato.prediction.backtest import run_backtest
from zksato.prediction.core import Position, RiskLimits, Tick
from zksato.prediction.data import SyntheticTickGenerator
from zksato.prediction.strategy import ProbabilityEdgeStrategy
from zksato.risk import RiskEngine


class FakePredictionClient:
    def __init__(self) -> None:
        self.orders: list[dict[str, object]] = []

    async def create_order(self, market_id: str, side: str, amount_usd: float) -> dict[str, object]:
        order = {
            "id": f"pred-{len(self.orders) + 1}",
            "market_id": market_id,
            "side": side,
            "amount": amount_usd,
            "price": 0.5,
            "status": "filled",
        }
        self.orders.append(order)
        return order

    async def cancel_order(self, order_id: str) -> dict[str, object]:
        return {"id": order_id, "market_id": "BTC-5MIN", "side": "UP", "amount": 1, "price": 0.5, "status": "canceled"}

    async def fetch_open_orders(self, market_id: str) -> list[dict[str, object]]:
        return []

    async def fetch_balance(self) -> dict[str, object]:
        return {"cash": 1000.0}


@pytest.mark.asyncio
async def test_prediction_broker_place_order_updates_residual() -> None:
    settings = Settings(prediction_enabled=True)
    client = FakePredictionClient()
    broker = PredictionBroker(settings, client=client)
    record = await broker.place_order(
        OrderIntent(
            symbol="BTC-5MIN",
            side=Side.UP,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=0.55,
            source="test",
        )
    )
    assert record.status == OrderStatus.FILLED
    assert record.side == Side.UP
    assert broker.directional_residual("BTC-5MIN") == 10.0
    assert broker.complete_set_cost("BTC-5MIN") > 0


@pytest.mark.asyncio
async def test_prediction_broker_rejects_when_not_enabled() -> None:
    settings = Settings(prediction_enabled=False)
    with pytest.raises(RuntimeError, match="not enabled"):
        PredictionBroker(settings)


@pytest.mark.asyncio
async def test_prediction_broker_cancel_maps_response() -> None:
    settings = Settings(prediction_enabled=True)
    client = FakePredictionClient()
    broker = PredictionBroker(settings, client=client)
    record = await broker.cancel_order("pred-1")
    assert record.status == OrderStatus.CANCELLED


def test_prediction_strategy_generates_signal() -> None:
    strategy = ProbabilityEdgeStrategy(min_edge=0.01)
    tick = Tick(timestamp=1, spot=105.0, reference=100.0, up_ask=0.6, down_ask=0.4, volatility=0.02, momentum=0.5)
    signal = strategy.signal(tick)
    assert signal is not None
    assert signal.side in {Side.UP, Side.DOWN}


def test_prediction_strategy_returns_none_below_min_edge() -> None:
    strategy = ProbabilityEdgeStrategy(min_edge=0.99)
    tick = Tick(timestamp=1, spot=100.0, reference=100.0, up_ask=0.5, down_ask=0.5)
    signal = strategy.signal(tick)
    assert signal is None


def test_prediction_backtest_runs_with_synthetic_data() -> None:
    generator = SyntheticTickGenerator(seed=42)
    ticks = generator.generate(50)
    result = run_backtest(ticks, starting_cash=1000.0)
    assert result.fills >= 0
    assert result.ending_cash >= 0


def test_prediction_risk_engine_rejects_excessive_edge() -> None:
    engine = RiskEngine(Settings(min_prediction_edge=0.1))
    from zksato.domain import RiskContext
    decision = engine.evaluate(
        OrderIntent(symbol="BTC-5MIN", side=Side.UP, quantity=1, price=0.5),
        RiskContext(
            reference_price=0.5,
            quote_age_seconds=1.0,
            prediction_edge=0.05,
            prediction_directional_residual=10.0,
            prediction_complete_set_cost=0.5,
            market_data_available=True,
            price_band_ok=True,
            tick_size_ok=True,
            account_allowed=True,
            market_session_known=True,
            market_session_open=True,
        ),
    )
    assert decision.approved is False
    assert "model edge is below minimum threshold" in decision.reasons


def test_prediction_risk_engine_rejects_directional_residual() -> None:
    engine = RiskEngine(Settings(max_directional_residual=50.0))
    from zksato.domain import RiskContext
    decision = engine.evaluate(
        OrderIntent(symbol="BTC-5MIN", side=Side.UP, quantity=1, price=0.5),
        RiskContext(
            reference_price=0.5,
            quote_age_seconds=1.0,
            prediction_edge=0.1,
            prediction_directional_residual=60.0,
            prediction_complete_set_cost=0.5,
            market_data_available=True,
            price_band_ok=True,
            tick_size_ok=True,
            account_allowed=True,
            market_session_known=True,
            market_session_open=True,
        ),
    )
    assert decision.approved is False
    assert "directional residual exceeds configured maximum" in decision.reasons


def test_prediction_risk_engine_rejects_complete_set_cost() -> None:
    engine = RiskEngine(Settings(max_complete_set_cost=0.8))
    from zksato.domain import RiskContext
    decision = engine.evaluate(
        OrderIntent(symbol="BTC-5MIN", side=Side.DOWN, quantity=1, price=0.5),
        RiskContext(
            reference_price=0.5,
            quote_age_seconds=1.0,
            prediction_edge=0.1,
            prediction_directional_residual=10.0,
            prediction_complete_set_cost=0.9,
            market_data_available=True,
            price_band_ok=True,
            tick_size_ok=True,
            account_allowed=True,
            market_session_known=True,
            market_session_open=True,
        ),
    )
    assert decision.approved is False
    assert "complete-set cost exceeds configured maximum" in decision.reasons
