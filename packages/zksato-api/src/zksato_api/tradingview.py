"""TradingView webhook handler for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TradingViewWebhook:
    """Handles TradingView webhook alerts."""

    def parse_alert(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse TradingView alert payload."""
        return {
            "symbol": payload.get("symbol", ""),
            "action": payload.get("action", ""),
            "price": payload.get("price", 0),
            "strategy": payload.get("strategy", ""),
        }

    def validate_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Validate webhook signature."""
        import hashlib
        import hmac

        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
