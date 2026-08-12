from hypothesis import given
from hypothesis import strategies as st

from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, Side
from zksato.risk import RiskEngine


def context(price: float, **updates: object) -> RiskContext:
    values: dict[str, object] = {
        "reference_price": price,
        "portfolio_value": 1_000_000.0,
        "line_available": 10_000_000.0,
        "available_quantity": 1_000_000,
        "opens_new_position": False,
        "market_session_known": True,
        "market_session_open": True,
        "market_data_available": True,
        "price_band_ok": True,
        "tick_size_ok": True,
        "account_allowed": True,
    }
    values.update(updates)
    return RiskContext(**values)  # type: ignore[arg-type]


@given(
    quantity=st.integers(min_value=1, max_value=100_000),
    price=st.floats(min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False),
)
def test_kill_switch_always_rejects_buy(quantity: int, price: float) -> None:
    engine = RiskEngine(
        Settings(kill_switch=True, require_stop_loss=False, max_notional_per_order=1_000_000_000)
    )
    intent = OrderIntent(symbol="AOT", side=Side.BUY, quantity=quantity, price=price)
    decision = engine.evaluate(intent, context(price))
    assert decision.approved is False
    assert "global kill switch is active" in decision.reasons


@given(
    quantity=st.integers(min_value=2, max_value=100_000),
    available=st.integers(min_value=0, max_value=99_999),
)
def test_equity_sell_cannot_exceed_available_position(quantity: int, available: int) -> None:
    if available >= quantity:
        available = quantity - 1
    engine = RiskEngine(Settings(require_stop_loss=False, allow_equity_short_selling=False))
    intent = OrderIntent(symbol="PTT", side=Side.SELL, quantity=quantity, price=30.0)
    decision = engine.evaluate(
        intent, context(30.0, available_quantity=available, reduces_exposure=True)
    )
    assert decision.approved is False
    assert "sell quantity exceeds available position" in decision.reasons


@given(
    extra_age=st.floats(min_value=0.001, max_value=10_000, allow_nan=False, allow_infinity=False)
)
def test_stale_quote_always_rejects(extra_age: float) -> None:
    settings = Settings(require_stop_loss=False, market_data_stale_seconds=5.0)
    engine = RiskEngine(settings)
    intent = OrderIntent(symbol="KBANK", side=Side.BUY, quantity=1, price=100.0)
    decision = engine.evaluate(intent, context(100.0, quote_age_seconds=5.0 + extra_age))
    assert decision.approved is False
    assert "market quote is stale" in decision.reasons


@given(
    price=st.floats(min_value=1.0, max_value=10_000, allow_nan=False, allow_infinity=False),
    quantity=st.integers(min_value=1, max_value=100_000),
)
def test_notional_limit_is_fail_closed(price: float, quantity: int) -> None:
    notional = price * quantity
    if notional <= 1.0:
        return
    limit = max(0.01, notional / 2)
    engine = RiskEngine(Settings(require_stop_loss=False, max_notional_per_order=limit))
    intent = OrderIntent(symbol="CPALL", side=Side.BUY, quantity=quantity, price=price)
    decision = engine.evaluate(intent, context(price))
    assert decision.approved is False
    assert "order notional exceeds configured maximum" in decision.reasons
