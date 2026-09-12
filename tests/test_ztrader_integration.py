# ruff: noqa: I001
from fastapi.testclient import TestClient

from zksato.api import _ztrader_advisory_key, app, store


client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "version": "1.1",
        "tenant_id": "tenant-demo",
        "account_ref": "paper-account-1",
        "portfolio_ref": "portfolio-alpha",
        "signal_id": "signal-ztrader-001",
        "trace_id": "trace-ztrader-001",
        "symbol": "TOKEN",
        "chain": "base",
        "address": "0x1111111111111111111111111111111111111111",
        "scores": {"opportunity": 78, "risk": 31, "confidence": 74},
        "narrative": "EARLY",
        "whales": "ACCUMULATING",
        "rug_risk": "LOW",
        "action": "WATCH",
        "evidence_timestamp": "2026-09-12T11:00:00Z",
        "invalidations": ["risk score >= 55"],
        "proposed_trade": {
            "mode": "paper",
            "side": "buy",
            "order_type": "limit",
            "entry_low": 1.0,
            "entry_high": 1.1,
            "stop_loss": 0.9,
            "take_profit_levels": [1.3, 1.5],
            "max_position_usd": 100.0,
        },
        "evidence": {"source": "zworkforce:ztrader"},
    }


def test_ztrader_advisory_intake_is_non_executing() -> None:
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["execution_allowed"] is False
    assert body["risk_review_required"] is True
    assert body["canonical_executor"] == "zksato"
    assert body["mode"] == "paper"
    persisted = store.get_runtime_state(_ztrader_advisory_key("signal-ztrader-001"))
    assert persisted is not None
    assert persisted["intent"]["account_ref"] == "paper-account-1"
    assert persisted["intent"]["proposed_trade"]["mode"] == "paper"
    assert persisted["review_state"] == "pending_risk_review"
    assert persisted["submitted_by"]


def test_ztrader_advisory_intake_rejects_live_mode() -> None:
    payload = _payload()
    payload["proposed_trade"]["mode"] = "live"  # type: ignore[index]
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=payload)
    assert response.status_code == 422


def test_ztrader_advisory_intake_rejects_market_order() -> None:
    payload = _payload()
    payload["proposed_trade"]["order_type"] = "market"  # type: ignore[index]
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=payload)
    assert response.status_code == 422


def test_ztrader_advisory_intake_returns_conflict_outside_paper(monkeypatch) -> None:
    from zksato.api import settings

    monkeypatch.setattr(settings, "trading_mode", "sandbox")
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=_payload())
    assert response.status_code == 409
