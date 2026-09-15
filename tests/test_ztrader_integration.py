from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from zksato import api as api_module
from zksato.api import app
from zksato.ztrader import ZTraderAdvisoryIntent


client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "version": "1.1",
        "tenant_id": "tenant-demo",
        "account_ref": "paper-account",
        "signal_id": "signal-001",
        "trace_id": "trace-001",
        "symbol": "BTC/USDT",
        "chain": "ethereum",
        "address": "0x1111111111111111111111111111111111111111",
        "scores": {"opportunity": 75, "risk": 30, "confidence": 80},
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
            "entry_low": 100.0,
            "entry_high": 110.0,
            "stop_loss": 90.0,
            "take_profit_levels": [130.0],
            "max_position_usd": 1050.0,
        },
        "evidence": {"source": "contract-test"},
    }


def test_advisory_v11_maps_to_deterministic_order_intent() -> None:
    advisory = ZTraderAdvisoryIntent.model_validate(_payload())
    intent = advisory.to_order_intent()
    assert intent.symbol == "BTC/USDT"
    assert intent.side.value == "buy"
    assert intent.price == 105.0
    assert intent.quantity == 10.0
    assert intent.client_order_id == "ztrader:signal-001"
    assert intent.source == "ztrader-intel"


def test_advisory_rejects_live_mode() -> None:
    payload = _payload()
    payload["proposed_trade"] = {
        **payload["proposed_trade"],  # type: ignore[arg-type]
        "mode": "live",
    }
    with pytest.raises(ValueError):
        ZTraderAdvisoryIntent.model_validate(payload)


def test_ztrader_preflight_never_claims_live_execution() -> None:
    response = client.post("/v1/integrations/ztrader/preflight", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "paper"
    assert body["live_execution_allowed"] is False
    assert "decision" in body


def test_ztrader_submit_fails_closed_outside_paper_mode(monkeypatch) -> None:
    monkeypatch.setattr(api_module.settings, "trading_mode", "live")
    response = client.post("/v1/integrations/ztrader/paper-orders", json=_payload())
    assert response.status_code == 409
    assert "restricted to paper mode" in response.json()["detail"]
