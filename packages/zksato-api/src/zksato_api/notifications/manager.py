"""Notification manager for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NotificationManager:
    """Manages notifications via multiple channels."""

    def send_telegram(self, message: str, chat_id: str | None = None) -> bool:
        """Send Telegram notification."""
        return True

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email notification."""
        return True

    def send_webhook(self, url: str, payload: dict[str, Any]) -> bool:
        """Send webhook notification."""
        return True

    def notify_order(self, order_data: dict[str, Any]) -> None:
        """Notify about order event."""
        pass

    def notify_fill(self, fill_data: dict[str, Any]) -> None:
        """Notify about fill event."""
        pass

    def notify_risk_rejection(self, rejection_data: dict[str, Any]) -> None:
        """Notify about risk rejection."""
        pass
