from __future__ import annotations

import hashlib
import hmac

from fastapi.testclient import TestClient

from zksato.api import app
from zksato.tradingview import (
    TradingViewAlertParser,
    TradingViewConfigStore,
    TradingViewWebhookValidator,
)

client = TestClient(app)


def test_webhook_hmac_validation_rejects_bad_signature() -> None:
    validator = TradingViewWebhookValidator(secret="mysecret")
    payload = b'{"symbol":"AOT","action":"buy","price":100.0,"strategy":"ema"}'
    assert validator.validate(payload, "badsignature") is False


def test_webhook_hmac_validation_accepts_valid_signature() -> None:
    secret = "mysecret"
    validator = TradingViewWebhookValidator(secret=secret)
    payload = b'{"symbol":"AOT","action":"buy","price":100.0,"strategy":"ema"}'
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert validator.validate(payload, signature) is True


def test_webhook_hmac_validation_allows_empty_secret() -> None:
    validator = TradingViewWebhookValidator(secret=None)
    payload = b'{"symbol":"AOT","action":"buy","price":100.0,"strategy":"ema"}'
    assert validator.validate(payload, None) is True


def test_alert_parser_buy_signal() -> None:
    parser = TradingViewAlertParser()
    signal = parser.parse(
        {"symbol": "aot", "action": "buy", "price": 100.5, "strategy": "ema_cross"}
    )
    assert signal is not None
    assert signal.symbol == "AOT"
    assert signal.action.value == "buy"
    assert signal.price == 100.5
    assert signal.strategy == "ema_cross"


def test_alert_parser_sell_signal() -> None:
    parser = TradingViewAlertParser()
    signal = parser.parse(
        {"symbol": "PTT", "action": "sell", "price": 50.0, "strategy": "momentum"}
    )
    assert signal is not None
    assert signal.symbol == "PTT"
    assert signal.action.value == "sell"


def test_alert_parser_rejects_hold() -> None:
    parser = TradingViewAlertParser()
    assert (
        parser.parse({"symbol": "AOT", "action": "hold", "price": 100.0, "strategy": "ema"}) is None
    )


def test_alert_parser_rejects_invalid_price() -> None:
    parser = TradingViewAlertParser()
    assert parser.parse({"symbol": "AOT", "action": "buy", "price": -10, "strategy": "ema"}) is None
    assert parser.parse({"symbol": "AOT", "action": "buy", "price": 0, "strategy": "ema"}) is None


def test_alert_parser_rejects_missing_fields() -> None:
    parser = TradingViewAlertParser()
    assert parser.parse({"symbol": "AOT"}) is None
    assert parser.parse({"action": "buy"}) is None


def test_config_store_roundtrip() -> None:
    store = TradingViewConfigStore()
    store.set_webhook_secret("AOT", "secret123")
    assert store.get_webhook_secret("AOT") == "secret123"
    assert store.get_webhook_secret("aot") == "secret123"
    assert store.get_webhook_secret("PTT") is None
    items = store.list_webhooks()
    assert len(items) == 1
    assert items[0]["symbol"] == "AOT"
    assert store.delete_webhook_secret("AOT") is True
    assert store.get_webhook_secret("AOT") is None
    assert store.delete_webhook_secret("AOT") is False


def test_tradingview_endpoint_rejects_invalid_json() -> None:
    response = client.post(
        "/v1/tradingview/webhook",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_tradingview_endpoint_accepts_valid_payload_without_auth() -> None:
    response = client.post(
        "/v1/tradingview/webhook",
        json={"symbol": "AOT", "action": "buy", "price": 100.0, "strategy": "ema"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
