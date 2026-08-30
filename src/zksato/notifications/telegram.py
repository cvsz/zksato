from __future__ import annotations

from typing import Any

import httpx


class TelegramNotifier:
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._enabled = bool(bot_token and chat_id)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send(self, message: str) -> bool:
        if not self._enabled:
            return False
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return True
        except (httpx.HTTPError, OSError, ValueError):
            return False

    async def send_order_alert(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str,
        price: float | None = None,
        strategy: str = "manual",
    ) -> bool:
        price_str = f" @ ${price:.2f}" if price else " @ MARKET"
        text = (
            f"⚡ *[ORDER SUBMITTED]*\n"
            f"• *Strategy:* `{strategy}`\n"
            f"• *Symbol:* `{symbol}`\n"
            f"• *Side:* *{side.upper()}* {quantity} contracts{price_str}\n"
            f"• *Type:* `{order_type.upper()}`\n"
            f"• *Mode:* `Paper Execution`"
        )
        return await self.send(text)

    async def send_fill_alert(
        self,
        symbol: str,
        side: str,
        quantity: int,
        fill_price: float,
        commission: float = 0.0,
    ) -> bool:
        text = (
            f"✅ *[FILL EXECUTED]*\n"
            f"• *Symbol:* `{symbol}`\n"
            f"• *Side:* *{side.upper()}* {quantity} contracts\n"
            f"• *Execution Price:* `${fill_price:.4f}`\n"
            f"• *Commission:* `${commission:.2f}`"
        )
        return await self.send(text)

    async def send_kill_switch_alert(self, active: bool, actor: str = "operator") -> bool:
        if active:
            text = (
                f"🚨 *[EMERGENCY KILL SWITCH ENGAGED]*\n"
                f"• *Triggered by:* `{actor}`\n"
                f"• *Action:* All automated execution HALTED immediately\n"
                f"• *Status:* CRITICAL DEFENSE ACTIVE"
            )
        else:
            text = (
                f"🟢 *[KILL SWITCH DEACTIVATED]*\n"
                f"• *Cleared by:* `{actor}`\n"
                f"• *Action:* Automated execution resumed under risk guardrails"
            )
        return await self.send(text)

    async def send_bot_status(self, bot_id: str, state: str, reason: str | None = None) -> bool:
        icon = "🟢" if state == "running" else "⏸️" if state == "paused" else "🛑"
        reason_str = f"\n• *Reason:* `{reason}`" if reason else ""
        text = (
            f"{icon} *[BOT STATE CHANGE]*\n"
            f"• *Bot ID:* `{bot_id}`\n"
            f"• *New State:* `{state.upper()}`"
            f"{reason_str}"
        )
        return await self.send(text)
