"""Market data panel component for zksato TUI.

Displays real-time market quotes for SET/TFEX symbols.
"""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from textual.reactive import reactive
from textual.widget import Widget

from ..styles import format_number


class MarketPanel(Widget):
    """Market data display panel."""

    DEFAULT_CSS = """
    MarketPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1;
    }
    """

    quotes: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._quotes: list[dict[str, Any]] = []

    def update_quotes(self, quotes: list[dict[str, Any]]) -> None:
        """Update market quotes."""
        self._quotes = quotes
        self.quotes = quotes
        self.refresh()

    def add_quote(self, symbol: str, price: float, change_pct: float, volume: int) -> None:
        """Add or update a quote."""
        for i, q in enumerate(self._quotes):
            if q.get("symbol") == symbol:
                self._quotes[i] = {
                    "symbol": symbol,
                    "price": price,
                    "change_pct": change_pct,
                    "volume": volume,
                }
                break
        else:
            self._quotes.append(
                {
                    "symbol": symbol,
                    "price": price,
                    "change_pct": change_pct,
                    "volume": volume,
                }
            )
        self.quotes = self._quotes
        self.refresh()

    def clear(self) -> None:
        """Clear all quotes."""
        self._quotes = []
        self.quotes = []
        self.refresh()

    def render(self) -> Panel:
        """Render the market panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Symbol", style="cyan", width=10)
        table.add_column("Price", style="white", width=12)
        table.add_column("Change %", style="green", width=10)
        table.add_column("Volume", style="dim", width=12)

        if not self._quotes:
            table.add_row("-", "-", "-", "-")
        else:
            for quote in self._quotes:
                symbol = quote.get("symbol", "-")
                price = quote.get("last", quote.get("price", 0))
                change_pct = quote.get("change_pct", 0)
                volume = quote.get("volume", 0)

                change_color = "green" if change_pct >= 0 else "red"
                table.add_row(
                    symbol,
                    format_number(price, 2),
                    f"[{change_color}]{change_pct:+.2f}%[/]",
                    format_number(volume, 0),
                )

        return Panel(
            table,
            title="Market Data",
            border_style="cyan",
            title_align="left",
        )
