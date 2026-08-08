from zksato.config import Settings
from zksato.tfex import (
    TfexOrderIntent,
    TfexOrderSubmission,
    TfexPosition,
    TfexRiskContext,
    TfexRiskEngine,
    TfexSide,
)


def test_tfex_risk_rejects_stale_and_contract_limit() -> None:
    engine = TfexRiskEngine(Settings(max_tfex_contracts=5, market_data_stale_seconds=5))
    submission = TfexOrderSubmission(
        intent=TfexOrderIntent(
            symbol="S50Z26",
            side=TfexSide.LONG,
            position=TfexPosition.OPEN,
            volume=2,
            price=900,
        ),
        risk=TfexRiskContext(current_contracts=4, quote_age_seconds=6),
    )
    decision = engine.evaluate(submission)
    assert decision.approved is False
    assert "maximum TFEX contract exposure exceeded" in decision.reasons
    assert "market quote is stale" in decision.reasons
