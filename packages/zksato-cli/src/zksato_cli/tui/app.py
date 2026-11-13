"""Main TUI application for zksato.

A terminal user interface for interacting with the zksato trading platform.
Provides chat with agents, market data display, risk monitoring, and
order management through a terminal interface.

All order execution routes through the RiskEngine via the REST API,
preserving all AGENTS.md safety invariants.
"""

from __future__ import annotations

import asyncio
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

from .api_client import ZKSATOAPIClient
from .components.chat import ChatPanel
from .components.input import InputPanel, InputSubmitted
from .components.market import MarketPanel
from .components.risk import RiskPanel
from .components.sessions import SessionsPanel
from .components.tools import ToolPanel
from .config import TUIConfig


class ZKSATOTUI(App):
    """Main zksato TUI application."""

    CSS = """
    #main-container {
        height: 1fr;
    }

    #left-column {
        width: 1fr;
        height: 1fr;
    }

    #right-column {
        width: 1fr;
        height: 1fr;
    }

    #top-row {
        height: 1fr;
    }

    #bottom-row {
        height: 1fr;
    }

    ChatPanel {
        height: 1fr;
    }

    InputPanel {
        height: 3;
    }

    ToolPanel {
        height: 1fr;
    }

    SessionsPanel {
        height: 1fr;
    }

    RiskPanel {
        height: 1fr;
    }

    MarketPanel {
        height: 1fr;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("c", "clear_chat", "Clear Chat"),
        Binding("r", "refresh_data", "Refresh Data"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, config: TUIConfig | None = None) -> None:
        super().__init__()
        self.config = config or TUIConfig()
        self.api_client: ZKSATOAPIClient | None = None
        self._update_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            with Horizontal(id="left-column"):
                with Vertical(id="top-row"):
                    yield ChatPanel(id="chat-panel")
                    yield InputPanel(id="input-panel")
                with Vertical(id="bottom-row"):
                    yield ToolPanel(id="tool-panel")

            with Horizontal(id="right-column"):
                with Vertical(id="top-row"):
                    yield SessionsPanel(id="sessions-panel")
                with Vertical(id="bottom-row"):
                    yield RiskPanel(id="risk-panel")
                    yield MarketPanel(id="market-panel")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the TUI after mount."""
        self.api_client = ZKSATOAPIClient(
            base_url=self.config.api_base_url,
            api_key=self.config.api_key,
        )

        # Try to connect to API
        try:
            health = await self.api_client.health()
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Connected to zksato API: {health.get('status', 'unknown')}"
            )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Warning: Could not connect to API: {exc}"
            )

        # Start background data refresh
        self._update_task = asyncio.create_task(self._periodic_refresh())

        # Focus the input panel
        self.query_one("#input-panel", InputPanel).focus()

    async def on_unmount(self) -> None:
        """Clean up on unmount."""
        if self._update_task:
            self._update_task.cancel()
        if self.api_client:
            await self.api_client.close()

    async def on_input_submitted(self, message: InputSubmitted) -> None:
        """Handle input submission from the input panel."""
        text = message.value
        if not text.strip():
            return

        # Add user message to chat
        self.query_one("#chat-panel", ChatPanel).add_user_message(text)

        # Clear input
        self.query_one("#input-panel", InputPanel).clear()

        # Process the command
        await self._process_input(text)

    async def _process_input(self, text: str) -> None:
        """Process user input through the API."""
        # Parse command
        parts = text.strip().split()
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]

        try:
            if command == "/quote" and args:
                await self._handle_quote(args[0])
            elif command == "/orders":
                await self._handle_orders()
            elif command == "/portfolio":
                await self._handle_portfolio()
            elif command == "/risk":
                await self._handle_risk()
            elif command == "/sessions":
                await self._handle_sessions()
            elif command == "/help":
                self._show_help()
            else:
                # Treat as a general message to the agent
                self.query_one("#chat-panel", ChatPanel).add_system_message(
                    f"Unknown command: {text}. Type /help for available commands."
                )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Error: {exc}"
            )

    async def _handle_quote(self, symbol: str) -> None:
        """Handle quote command."""
        try:
            quote = await self.api_client.get_market_quote(symbol)
            price = quote.get("last", 0)
            change_pct = quote.get("change_pct", 0)
            volume = quote.get("volume", 0)
            self.query_one("#chat-panel", ChatPanel).add_agent_message(
                f"Quote for {symbol}: {price} ({change_pct:+.2f}%), Volume: {volume}"
            )
            # Update market panel
            market_panel = self.query_one("#market-panel", MarketPanel)
            market_panel.add_quote(symbol, price, change_pct, volume)
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Failed to get quote: {exc}"
            )

    async def _handle_orders(self) -> None:
        """Handle orders command."""
        try:
            orders = await self.api_client.get_orders()
            self.query_one("#chat-panel", ChatPanel).add_agent_message(
                f"Open orders: {len(orders)}"
            )
            for order in orders[:5]:
                symbol = order.get("symbol", "-")
                side = order.get("side", "-")
                qty = order.get("quantity", 0)
                price = order.get("price", 0)
                self.query_one("#chat-panel", ChatPanel).add_agent_message(
                    f"  {symbol} {side} {qty} @ {price}"
                )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Failed to get orders: {exc}"
            )

    async def _handle_portfolio(self) -> None:
        """Handle portfolio command."""
        try:
            portfolio = await self.api_client.get_portfolio()
            self.query_one("#chat-panel", ChatPanel).add_agent_message(
                f"Portfolio: {portfolio}"
            )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Failed to get portfolio: {exc}"
            )

    async def _handle_risk(self) -> None:
        """Handle risk command."""
        try:
            evaluations = await self.api_client.get_risk_evaluations()
            self.query_one("#chat-panel", ChatPanel).add_agent_message(
                f"Risk evaluations: {len(evaluations)}"
            )
            for eval_ in evaluations[:5]:
                approved = eval_.get("approved", False)
                reasons = eval_.get("reasons", [])
                self.query_one("#chat-panel", ChatPanel).add_risk_decision(
                    approved, reasons
                )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Failed to get risk evaluations: {exc}"
            )

    async def _handle_sessions(self) -> None:
        """Handle sessions command."""
        try:
            sessions = await self.api_client.get_agent_sessions()
            sessions_panel = self.query_one("#sessions-panel", SessionsPanel)
            for session in sessions:
                sessions_panel.add_session(session)
            self.query_one("#chat-panel", ChatPanel).add_agent_message(
                f"Active sessions: {len(sessions)}"
            )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Failed to get sessions: {exc}"
            )

    def _show_help(self) -> None:
        """Show help message."""
        help_text = """
Available commands:
  /quote <symbol>  - Get market quote for a symbol
  /orders          - List open orders
  /portfolio       - Show portfolio snapshot
  /risk            - Show risk evaluations
  /sessions        - List agent sessions
  /help            - Show this help message
  /clear           - Clear chat
        """
        self.query_one("#chat-panel", ChatPanel).add_system_message(help_text)

    async def _periodic_refresh(self) -> None:
        """Periodically refresh market data and risk status."""
        while True:
            await asyncio.sleep(5)
            try:
                if self.api_client:
                    quotes = await self.api_client.list_quotes()
                    market_panel = self.query_one("#market-panel", MarketPanel)
                    market_panel.update_quotes(quotes)

                    risk_evals = await self.api_client.get_risk_evaluations()
                    if risk_evals:
                        latest = risk_evals[-1]
                        risk_panel = self.query_one("#risk-panel", RiskPanel)
                        risk_panel.update_risk(latest)
            except Exception:
                pass  # Silently ignore refresh errors

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    async def action_clear_chat(self) -> None:
        """Clear the chat panel."""
        self.query_one("#chat-panel", ChatPanel).clear()

    async def action_refresh_data(self) -> None:
        """Refresh all data."""
        try:
            if self.api_client:
                quotes = await self.api_client.list_quotes()
                market_panel = self.query_one("#market-panel", MarketPanel)
                market_panel.update_quotes(quotes)

                risk_evals = await self.api_client.get_risk_evaluations()
                if risk_evals:
                    latest = risk_evals[-1]
                    risk_panel = self.query_one("#risk-panel", RiskPanel)
                    risk_panel.update_risk(latest)

                self.query_one("#chat-panel", ChatPanel).add_system_message(
                    "Data refreshed."
                )
        except Exception as exc:
            self.query_one("#chat-panel", ChatPanel).add_system_message(
                f"Refresh failed: {exc}"
            )
