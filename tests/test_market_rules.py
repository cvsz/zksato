from datetime import UTC, datetime

from zksato.market_rules import InstrumentMetadata, InstrumentRegistry, MarketSessionPolicy


def test_instrument_registry_validates_price_band_and_tick() -> None:
    registry = InstrumentRegistry()
    registry.upsert(
        InstrumentMetadata(
            symbol="AOT",
            sector="TRANSPORT",
            tick_size=0.25,
            lower_price_band=30,
            upper_price_band=50,
        )
    )
    assert registry.validate_price("AOT", 40.25) == (True, True, True)
    assert registry.validate_price("AOT", 40.10) == (True, True, False)
    assert registry.validate_price("AOT", 55.00) == (True, False, True)
    assert registry.sector_for("aot") == "TRANSPORT"


def test_market_session_policy_is_deterministic() -> None:
    policy = MarketSessionPolicy("Asia/Bangkok", "09:30-12:30,14:00-16:30")
    known, opened = policy.state(datetime(2026, 8, 10, 3, 0, tzinfo=UTC))
    assert known is True
    assert opened is True
    _, closed = policy.state(datetime(2026, 8, 9, 3, 0, tzinfo=UTC))
    assert closed is False
