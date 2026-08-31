from __future__ import annotations

from typing import Any

import httpx


def _escape_md(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("`", "\\`")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


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
            f"• *Strategy:* `{_escape_md(strategy)}`\n"
            f"• *Symbol:* `{_escape_md(symbol)}`\n"
            f"• *Side:* *{_escape_md(side.upper())}* {quantity} contracts{price_str}\n"
            f"• *Type:* `{_escape_md(order_type.upper())}`\n"
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
            f"• *Symbol:* `{_escape_md(symbol)}`\n"
            f"• *Side:* *{_escape_md(side.upper())}* {quantity} contracts\n"
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
            f"• *Strategy:* `{_escape_md(strategy)}`\n"
            f"• *Ticker:* `{_escape_md(ticker)}` ({_escape_md(interval)})\n"
            f"• *Signal:* *{_escape_md(action.upper())}*{price_str}\n"
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

    async def handle_telegram_command(
        self,
        command: str,
        chat_id: str | int,
        *,
        system_status: dict[str, Any] | None = None,
        portfolio_summary: dict[str, Any] | None = None,
        quotes: list[dict[str, Any]] | None = None,
    ) -> str:
        cmd = command.strip().lower()
        if cmd.startswith("/"):
            cmd = cmd[1:]
        cmd = cmd.split("@")[0].strip()

        if cmd in {"start", "help"}:
            return (
                "🤖 *[zKSato Automated Trading Bot]*\n\n"
                "Available Commands:\n"
                "• `/status` - System health, mode & kill switch\n"
                "• `/pnl` - Real-time portfolio P&L summary\n"
                "• `/bots` - Active strategies and symbols\n"
                "• `/var` - Value-at-Risk calculation\n"
                "• `/quotes` - Spot market tickers\n"
                "• `/kill` - Emergency Kill Switch HALT\n"
                "• `/resume` - Clear Kill Switch\n"
                "• `/help` - Show this menu"
            )

        if cmd == "status":
            env = system_status.get("environment", "dev") if system_status else "dev"
            mode = system_status.get("execution_mode", "paper") if system_status else "paper"
            ks = system_status.get("kill_switch_active", False) if system_status else False
            ks_text = "🚨 ENGAGED (HALTED)" if ks else "🟢 SAFE (OPERATIONAL)"
            return (
                f"🛡️ *[SYSTEM STATUS]*\n"
                f"• *Environment:* `{env.upper()}`\n"
                f"• *Execution Mode:* `{mode.upper()}`\n"
                f"• *Kill Switch:* *{ks_text}*\n"
                f"• *Terminal:* [Launch Dashboard](https://zksato.zeaz.dev/en/dashboard)"
            )

        if cmd == "pnl":
            total = portfolio_summary.get("total", 0.0) if portfolio_summary else 0.0
            cur = portfolio_summary.get("currency", "USDT") if portfolio_summary else "USDT"
            sign = "+" if total >= 0 else ""
            return (
                f"📊 *[PORTFOLIO P&L]*\n"
                f"• *Realized + Unrealized:* `{sign}${total:,.2f} {cur}`\n"
                f"• *Status:* Live Tracking Active"
            )

        if cmd == "quotes":
            if not quotes:
                return "📈 *[SPOT QUOTES]*\nNo active market quotes available."
            lines = ["📈 *[SPOT QUOTES]*"]
            for q in quotes[:8]:
                sym = q.get("symbol", "UNKNOWN")
                price = q.get("price", q.get("last", 0.0))
                lines.append(f"• *{sym}:* `${price:,.2f}`")
            return "\n".join(lines)

        return f"❓ Unknown command `/{cmd}`. Type `/help` for available options."
