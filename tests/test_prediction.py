import pytest

from zksato.broker.prediction import PredictionBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderStatus, OrderType, Side
from zksato.prediction.backtest import run_backtest
from zksato.prediction.core import Tick
from zksato.prediction.data import SyntheticTickGenerator
from zksato.prediction.strategy import ProbabilityEdgeStrategy
from zksato.risk import RiskEngine


class FakePredictionClient:
    def __init__(self) -> None:
        self.orders: list[dict[str, object]] = []

    async def create_order(
        self, market_id: str, side: str, amount_usd: float, price: float
    ) -> dict[str, object]:
        order = {
            "id": f"pred-{len(self.orders) + 1}",
            "market_id": market_id,
            "side": side,
            "amount": amount_usd,
            "price": price,
            "status": "filled",
        }
        self.orders.append(order)
        return order

    async def cancel_order(self, order_id: str) -> dict[str, object]:
        return {
            "id": order_id,
            "market_id": "BTC-5MIN",
            "side": "UP",
            "amount": 1,
            "price": 0.5,
            "status": "canceled",
        }

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
    tick = Tick(
        timestamp=1,
        spot=105.0,
        reference=100.0,
        up_ask=0.6,
        down_ask=0.4,
        volatility=0.02,
        momentum=0.5,
    )
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


def test_prediction_live_gate_enforces_safety_invariants() -> None:
    from zksato.prediction.live import PredictionLiveGate

    # Case 1: prediction not enabled
    gate = PredictionLiveGate(Settings(prediction_enabled=False))
    with pytest.raises(RuntimeError, match="not enabled"):
        gate.validate()

    # Case 2: live trading disabled by policy
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=False))
    with pytest.raises(RuntimeError, match="disabled by server policy"):
        gate.validate()

    # Case 3: acknowledge loss not set
    gate = PredictionLiveGate(Settings(prediction_enabled=True, prediction_enable_live=True))
    with pytest.raises(RuntimeError, match="acknowledge loss is required"):
        gate.validate()

    # Case 4: adapter review not set
    gate.acknowledge_loss = True
    with pytest.raises(RuntimeError, match="adapter review is required"):
        gate.validate()

    # Case 5: kill switch readiness not set
    gate.reviewed_adapter = True
    with pytest.raises(RuntimeError, match="kill switch readiness is required"):
        gate.validate()

    # Case 6: all prerequisites met, but no live venue adapter is attached
    gate.kill_switch_ready = True
    with pytest.raises(RuntimeError, match="no reviewed venue adapter attached"):
        gate.validate()


def test_paper_prediction_broker_fills_and_settles_correctly() -> None:
    from zksato.prediction.broker import PaperPredictionBroker
    from zksato.prediction.core import RiskLimits

    limits = RiskLimits(
        max_order_usd=500, max_market_exposure_usd=2000, max_directional_shares=2000
    )
    broker = PaperPredictionBroker(Settings(), limits=limits)

    fill = broker.execute(Side.UP, 0.55, 100.0)
    assert fill.side == Side.UP
    assert fill.shares > 0
    assert fill.price >= 0.55
    assert len(broker.fills) == 1
    assert broker.cash < broker.starting_cash

    pnl = broker.settle(Side.UP)
    assert isinstance(pnl, float)


def test_paper_prediction_broker_rejects_invalid_price() -> None:
    from zksato.prediction.broker import PaperPredictionBroker, RiskRejected

    broker = PaperPredictionBroker(Settings())
    with pytest.raises(RiskRejected, match="price must be between 0 and 1"):
        broker.execute(Side.UP, 0.0, 5.0)
    with pytest.raises(RiskRejected, match="price must be between 0 and 1"):
        broker.execute(Side.UP, 1.0, 5.0)


def test_paper_prediction_broker_rejects_zero_order() -> None:
    from zksato.prediction.broker import PaperPredictionBroker, RiskRejected

    broker = PaperPredictionBroker(Settings())
    with pytest.raises(RiskRejected, match="order exceeds configured order limit"):
        broker.execute(Side.UP, 0.5, 0.0)


def test_paper_prediction_broker_rejects_directional_overexposure() -> None:
    from zksato.prediction.broker import PaperPredictionBroker, RiskRejected
    from zksato.prediction.core import RiskLimits

    # max_directional_shares=1 means even 2 shares UP triggers rejection
    limits = RiskLimits(max_order_usd=50, max_market_exposure_usd=50000, max_directional_shares=3.0)
    broker = PaperPredictionBroker(Settings(), limits=limits)
    broker.execute(Side.UP, 0.5, 1.0)  # first fill: ~2 UP shares, residual=2 < 3, passes
    with pytest.raises(RiskRejected, match="directional residual limit reached"):
        broker.execute(Side.UP, 0.5, 1.0)  # second fill: residual would be ~4 > 3, rejected


def test_paper_prediction_broker_rejects_insufficient_cash() -> None:
    from zksato.prediction.broker import PaperPredictionBroker, RiskRejected
    from zksato.prediction.core import RiskLimits

    limits = RiskLimits(
        max_order_usd=50000, max_market_exposure_usd=500000, max_directional_shares=999999
    )
    broker = PaperPredictionBroker(Settings(), limits=limits)
    broker.cash = 0.0
    with pytest.raises(RiskRejected, match="insufficient paper cash"):
        broker.execute(Side.UP, 0.5, 5.0)


@pytest.mark.asyncio
async def test_polymarket_clob_adapter_wired_with_fake_client() -> None:
    """PolymarketClobAdapter is now wired — with an injected http client it must
    return normalized quotes/order payloads and enforce credential/validation guards."""
    from zksato.prediction.live import PolymarketClobAdapter

    class _FakeResp:
        def __init__(self, data: object, status_code: int = 200) -> None:
            self._data = data
            self.status_code = status_code
            self.text = str(data)

        def json(self) -> object:
            return self._data

    class _FakeClient:
        async def get(self, url: str, params: dict[str, object] | None = None) -> _FakeResp:
            if "/book" in url:
                return _FakeResp({"bids": [{"price": "0.49"}], "asks": [{"price": "0.51"}]})
            return _FakeResp({"price": "0.55"})

        async def post(self, url: str, json: dict[str, object] | None = None) -> _FakeResp:
            payload = json or {}
            return _FakeResp(
                {
                    "order_id": "poly-1",
                    "market_id": str(payload.get("token_id", "mkt-1")),
                    "price": payload.get("price", 0.5),
                    "size": payload.get("size", 10),
                    "status": "open",
                }
            )

        async def delete(self, url: str) -> _FakeResp:
            return _FakeResp({"success": True})

        async def aclose(self) -> None:
            return None

    adapter = PolymarketClobAdapter(
        api_key="key123", api_secret="sec456", http_client=_FakeClient()
    )
    quote = await adapter.get_market_quote("mkt-1")
    assert quote["market_id"] == "mkt-1"
    placed = await adapter.place_order("mkt-1", Side.UP, 0.50, 10.0)
    assert placed["order_id"] == "poly-1"
    assert placed["status"] == "open"
    cancelled = await adapter.cancel_order("poly-1")
    assert cancelled is True

    # Validation guards remain
    with pytest.raises(ValueError, match="price must be between"):
        await adapter.place_order("mkt-1", Side.UP, 0.0, 10.0)


@pytest.mark.asyncio
async def test_prediction_live_gate_passes_with_compliant_adapter() -> None:
    """PredictionLiveGate.validate() passes when all safety flags are set
    and a concrete (non-scaffold) adapter is supplied."""
    from typing import Any

    from zksato.prediction.live import PredictionLiveGate, PredictionVenueAdapter

    class _StubAdapter(PredictionVenueAdapter):
        async def get_market_quote(self, market_id: str) -> dict[str, str | float]:
            return {"market_id": market_id, "up_ask": 0.51, "up_bid": 0.49}

        async def place_order(
            self, market_id: str, side: Side, price: float, order_usd: float
        ) -> dict[str, Any]:
            return {"order_id": "stub-1", "status": "submitted"}

        async def cancel_order(self, order_id: str) -> bool:
            return True

    gate = PredictionLiveGate(
        Settings(prediction_enabled=True, prediction_enable_live=True),
        adapter=_StubAdapter(),
    )
    gate.acknowledge_loss = True
    gate.reviewed_adapter = True
    gate.kill_switch_ready = True
    gate.validate()  # must not raise


def test_cpmm_liquidity_pool_dynamic_slippage() -> None:
    from zksato.prediction.broker import PaperPredictionBroker, RiskRejected
    from zksato.prediction.core import LiquidityPool, RiskLimits

    pool = LiquidityPool(up_reserve=1000.0, down_reserve=1000.0)
    assert pool.spot_up_price == 0.5
    assert pool.spot_down_price == 0.5

    # Small trade: minimal slippage
    shares_small, price_small, slippage_small = pool.quote_buy(Side.UP, 10.0)
    assert price_small > 0.50
    assert slippage_small < 250.0  # < 2.5%

    # Large trade: high slippage
    shares_large, price_large, slippage_large = pool.quote_buy(Side.UP, 500.0)
    assert price_large > price_small
    assert slippage_large > 2000.0  # > 20%

    # Broker integration with pool
    limits = RiskLimits(max_order_usd=500.0, max_slippage_bps=300.0)
    broker = PaperPredictionBroker(Settings(), limits=limits, pool=pool)

    # Order with low slippage succeeds
    fill = broker.execute(Side.UP, 0.50, 10.0)
    assert fill.shares > 0
    assert fill.price > 0.50

    # Order exceeding max slippage is rejected
    with pytest.raises(RiskRejected, match="slippage .* exceeds limit"):
        broker.execute(Side.UP, 0.50, 300.0)
