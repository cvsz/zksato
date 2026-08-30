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

    async def send_risk_rejection(
        self,
        symbol: str,
        reasons: list[str],
        attempted_notional: float = 0.0,
    ) -> bool:
        reasons_list = [f"  - `{r}`" for r in reasons]
        reasons_fmt = "\n".join(reasons_list) if reasons_list else "  - `Risk threshold exceeded`"
        text = (
            f"⛔ *[RISK REJECTION]*\n"
            f"• *Symbol:* `{symbol}`\n"
            f"• *Notional:* `${attempted_notional:,.2f}`\n"
            f"• *Violations:*\n{reasons_fmt}"
        )
        return await self.send(text)

    async def send_pnl_summary(
        self,
        total_pnl: float,
        daily_pnl_pct: float,
        open_positions: int,
        currency: str = "USDT",
    ) -> bool:
        icon = "📈" if total_pnl >= 0 else "📉"
        sign = "+" if total_pnl >= 0 else ""
        text = (
            f"{icon} *[DAILY PORTFOLIO P&L SUMMARY]*\n"
            f"• *Total Realized + Unrealized:* `{sign}${total_pnl:,.2f} {currency}`\n"
            f"• *Daily Return:* `{sign}{daily_pnl_pct:.2f}%`\n"
            f"• *Open Active Positions:* `{open_positions}`\n"
            f"• *Timestamp:* `UTC`"
        )
        return await self.send(text)

    async def send_var_alert(
        self,
        var_amount: float,
        var_pct: float,
        confidence_level: float = 0.95,
        horizon_days: int = 1,
    ) -> bool:
        text = (
            f"⚠️ *[PORTFOLIO VALUE-AT-RISK (VaR) ALERT]*\n"
            f"• *Confidence Level:* `{int(confidence_level * 100)}%`\n"
            f"• *Time Horizon:* `{horizon_days} Day(s)`\n"
            f"• *Parametric VaR:* `${var_amount:,.2f}` (`{var_pct:.2f}%` of equity)\n"
            f"• *Action:* Review portfolio exposure and leverage"
        )
        return await self.send(text)

    async def send_tradingview_signal(
        self,
        ticker: str,
        action: str,
        price: float | None = None,
        strategy: str = "TradingView Webhook",
        interval: str = "1h",
    ) -> bool:
        price_str = f" @ ${price:.2f}" if price else ""
        text = (
            f"📡 *[TRADINGVIEW WEBHOOK SIGNAL RECEIVED]*\n"
            f"• *Strategy:* `{strategy}`\n"
            f"• *Ticker:* `{ticker}` ({interval})\n"
            f"• *Signal:* *{action.upper()}*{price_str}\n"
            f"• *Status:* Routed to RiskEngine"
        )
        return await self.send(text)

    async def send_reconciliation_alert(
        self,
        status: str,
        unresolved_orders: int = 0,
        mismatched_positions: int = 0,
    ) -> bool:
        icon = "✅" if unresolved_orders == 0 and mismatched_positions == 0 else "⚠️"
        text = (
            f"{icon} *[BROKER RECONCILIATION RESULT]*\n"
            f"• *Status:* `{status.upper()}`\n"
            f"• *Unresolved Orders:* `{unresolved_orders}`\n"
            f"• *Mismatched Positions:* `{mismatched_positions}`\n"
            f"• *External Truth Source:* `Broker SET/TFEX State`"
        )
        return await self.send(text)
