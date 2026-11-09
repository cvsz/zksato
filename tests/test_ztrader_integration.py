# ruff: noqa: I001
from fastapi.testclient import TestClient

from zksato.api import _ztrader_advisory_key, app, settings, store


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
    key = _ztrader_advisory_key(
        "signal-ztrader-001",
        tenant_id="tenant-demo",
        account_ref="paper-account-1",
    )
    persisted = store.get_runtime_state(key)
    assert persisted is not None
    assert persisted["intent"]["account_ref"] == "paper-account-1"
    assert persisted["intent"]["proposed_trade"]["mode"] == "paper"
    assert persisted["review_state"] == "pending_risk_review"
    assert persisted["submitted_by"]


def test_ztrader_advisory_isolation_across_tenants() -> None:
    payload_a = _payload()
    payload_a["tenant_id"] = "tenant-A"
    payload_a["account_ref"] = "account-A"
    payload_a["signal_id"] = "common-signal-999"

    payload_b = _payload()
    payload_b["tenant_id"] = "tenant-B"
    payload_b["account_ref"] = "account-B"
    payload_b["signal_id"] = "common-signal-999"

    resp_a = client.post("/v1/integrations/ztrader/advisory-intents", json=payload_a)
    assert resp_a.status_code == 202

    resp_b = client.post("/v1/integrations/ztrader/advisory-intents", json=payload_b)
    assert resp_b.status_code == 202

    key_a = _ztrader_advisory_key(
        "common-signal-999",
        tenant_id="tenant-A",
        account_ref="account-A",
    )
    key_b = _ztrader_advisory_key(
        "common-signal-999",
        tenant_id="tenant-B",
        account_ref="account-B",
    )

    assert key_a != key_b
    state_a = store.get_runtime_state(key_a)
    state_b = store.get_runtime_state(key_b)
    assert state_a is not None and state_b is not None
    assert state_a["intent"]["tenant_id"] == "tenant-A"
    assert state_b["intent"]["tenant_id"] == "tenant-B"


def test_ztrader_advisory_rejects_missing_tenant_or_account() -> None:
    payload = _payload()
    payload["tenant_id"] = ""
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=payload)
    assert response.status_code == 422

    payload2 = _payload()
    payload2["account_ref"] = ""
    response2 = client.post("/v1/integrations/ztrader/advisory-intents", json=payload2)
    assert response2.status_code == 422


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
    monkeypatch.setattr(settings, "trading_mode", "sandbox")
    response = client.post("/v1/integrations/ztrader/advisory-intents", json=_payload())
    assert response.status_code == 409
