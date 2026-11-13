"""Sessions panel component for zksato TUI.

Displays agent sessions with their status, duration, and activity.
"""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from textual.reactive import reactive
from textual.widget import Widget


class SessionsPanel(Widget):
    """Agent sessions display panel."""

    DEFAULT_CSS = """
    SessionsPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1;
    }
    """

    sessions: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._sessions: list[dict[str, Any]] = []

    def add_session(self, session_data: dict[str, Any]) -> None:
        """Add or update a session."""
        session_id = session_data.get("session_id", "unknown")
        for i, s in enumerate(self._sessions):
            if s.get("session_id") == session_id:
                self._sessions[i] = session_data
                break
        else:
            self._sessions.append(session_data)
        self.sessions = self._sessions
        self.refresh()

    def remove_session(self, session_id: str) -> None:
        """Remove a session."""
        self._sessions = [s for s in self._sessions if s.get("session_id") != session_id]
        self.sessions = self._sessions
        self.refresh()

    def clear(self) -> None:
        """Clear all sessions."""
        self._sessions = []
        self.sessions = []
        self.refresh()

    def render(self) -> Panel:
        """Render the sessions panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Session ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Subaccount", style="magenta")
        table.add_column("Created", style="dim")

        if not self._sessions:
            table.add_row("-", "-", "-", "-")
        else:
            for session in self._sessions:
                session_id = session.get("session_id", "unknown")[:12]
                status = session.get("status", "unknown")
                subaccount = session.get("subaccount_id", "default")[:12]
                created = session.get("created_at", "unknown")

                table.add_row(session_id, status, subaccount, created)

        return Panel(
            table,
            title="Agent Sessions",
            border_style="cyan",
            title_align="left",
        )
