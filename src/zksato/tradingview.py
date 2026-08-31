from __future__ import annotations

import hashlib
import hmac
import threading

from zksato.domain import Signal, SignalAction


class TradingViewWebhookValidator:
    def __init__(self, secret: str | None) -> None:
        self._secret = secret

    def validate(self, payload: bytes, signature: str | None) -> bool:
        if not self._secret:
            return False
        if not signature:
            return False
        expected = hmac.new(
            self._secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class TradingViewAlertParser:
    def parse(self, payload: object) -> Signal | None:
        if not isinstance(payload, dict):
            return None
        symbol = payload.get("symbol")
        action = payload.get("action")
        price = payload.get("price")
        strategy = payload.get("strategy")
        if not symbol or not action or price is None or not strategy:
            return None
        try:
            normalized_symbol = str(symbol).strip().upper()
            normalized_action = SignalAction(str(action).strip().lower())
            normalized_price = float(price)
            normalized_strategy = str(strategy).strip()
        except (TypeError, ValueError):
            return None
        if normalized_action not in (SignalAction.BUY, SignalAction.SELL):
            return None
        if normalized_price <= 0:
            return None
        if not normalized_symbol or not normalized_strategy:
            return None
        return Signal(
            symbol=normalized_symbol,
            strategy=normalized_strategy,
            action=normalized_action,
            price=normalized_price,
            confidence=0.5,
            reason="tradingview_webhook",
        )


class TradingViewConfigStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._secrets: dict[str, str] = {}
        self._alert_configs: dict[str, dict] = {}

    def set_webhook_secret(self, symbol: str, secret: str) -> None:
        with self._lock:
            self._secrets[symbol.strip().upper()] = secret

    def get_webhook_secret(self, symbol: str) -> str | None:
        with self._lock:
            return self._secrets.get(symbol.strip().upper())

    def delete_webhook_secret(self, symbol: str) -> bool:
        with self._lock:
            return self._secrets.pop(symbol.strip().upper(), None) is not None

    def set_alert_config(self, symbol: str, config: dict) -> None:
        with self._lock:
            self._alert_configs[symbol.strip().upper()] = config

    def get_alert_config(self, symbol: str) -> dict | None:
        with self._lock:
            return self._alert_configs.get(symbol.strip().upper())

    def list_webhooks(self) -> list[dict[str, object]]:
        with self._lock:
            return [
                {
                    "symbol": symbol,
                    "secret_configured": True,
                }
                for symbol in self._secrets
            ]
