"""Risk panel component for zksato TUI.

Displays risk engine evaluations, kill switch status, and risk limits.
"""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from textual.reactive import reactive
from textual.widget import Widget

from ..styles import format_pct, format_risk_level


class RiskPanel(Widget):
    """Risk evaluation display panel."""

    DEFAULT_CSS = """
    RiskPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1;
    }
    """

    risk_data: reactive[dict[str, Any]] = reactive({})

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self._risk_data: dict[str, Any] = {}

    def update_risk(self, data: dict[str, Any]) -> None:
        """Update risk data."""
        self._risk_data = data
        self.risk_data = data
        self.refresh()

    def render(self) -> Panel:
        """Render the risk panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="dim", width=20)
        table.add_column("Value", style="cyan")

        risk_level = self._risk_data.get("risk_level", "unknown")
        approved = self._risk_data.get("approved", False)
        reasons = self._risk_data.get("reasons", [])

        table.add_row("Risk Level", format_risk_level(risk_level).plain)
        table.add_row("Approved", "✅ YES" if approved else "❌ NO")

        if reasons:
            table.add_row("Reasons", "; ".join(reasons[:3]))

        daily_pnl = self._risk_data.get("daily_pnl_pct", 0)
        table.add_row("Daily P&L", format_pct(daily_pnl))

        drawdown = self._risk_data.get("drawdown_pct", 0)
        table.add_row("Drawdown", format_pct(drawdown))

        position_pct = self._risk_data.get("position_pct", 0)
        table.add_row("Position %", format_pct(position_pct))

        return Panel(
            table,
            title="Risk Engine",
            border_style="cyan",
            title_align="left",
        )
