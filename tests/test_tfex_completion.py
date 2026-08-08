from datetime import UTC, datetime, timedelta

from zksato.config import Settings
from zksato.tfex import (
    TfexContractMetadata,
    TfexContractRegistry,
    TfexOrderIntent,
    TfexOrderSubmission,
    TfexPosition,
    TfexRiskContext,
    TfexRiskEngine,
    TfexSide,
    settlement_pnl,
)


def test_tfex_contract_registry_and_settlement_pnl() -> None:
    registry = TfexContractRegistry()
    registry.upsert(
        TfexContractMetadata(
            symbol="S50U26",
            series="U26",
            multiplier=200,
            tick_size=0.1,
            expiry=datetime.now(UTC) + timedelta(days=30),
        )
    )
    assert registry.get("s50u26") is not None
    assert settlement_pnl(800, 805, 2, 200) == 2000


def test_tfex_open_order_fails_inside_expiry_window_and_bad_tick() -> None:
    settings = Settings(
        max_tfex_contracts=10,
        tfex_expiry_restriction_days=2,
        strict_tfex_reference_data=True,
    )
    engine = TfexRiskEngine(settings)
    intent = TfexOrderIntent(
        symbol="S50U26",
        side=TfexSide.LONG,
        position=TfexPosition.OPEN,
        volume=1,
        price=800.05,
    )
    decision = engine.evaluate(
        TfexOrderSubmission(
            intent=intent,
            risk=TfexRiskContext(
                market_data_available=True,
                contract_metadata_available=True,
                tick_size_ok=False,
                days_to_expiry=1,
                margin_usage_pct_after_trade=10,
            ),
        )
    )
    assert decision.approved is False
    assert any("tick size" in reason for reason in decision.reasons)
    assert any("expiry" in reason for reason in decision.reasons)
