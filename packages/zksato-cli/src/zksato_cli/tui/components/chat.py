"""Chat panel component for zksato TUI.

Displays conversation messages with agent, including tool calls,
risk evaluations, and order submissions. Supports streaming updates.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


class ChatMessage:
    """Represents a single chat message."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(UTC)
        self.metadata = metadata or {}


class ChatPanel(Widget):
    """Chat message display panel."""

    DEFAULT_CSS = """
    ChatPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1;
    }
    """

    messages: reactive[list[ChatMessage]] = reactive([])

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._messages: list[ChatMessage] = []

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a message to the chat."""
        msg = ChatMessage(role=role, content=content, metadata=metadata)
        self._messages.append(msg)
        self.messages = self._messages
        self.refresh()

    def add_agent_message(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add an agent message."""
        self.add_message("agent", content, metadata)

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message("user", content)

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self.add_message("system", content)

    def add_tool_call(self, tool_name: str, args: dict[str, Any], result: str) -> None:
        """Add a tool call message."""
        content = f"Tool: {tool_name}\nArgs: {args}\nResult: {result}"
        self.add_message("tool", content, {"tool": tool_name, "args": args, "result": result})

    def add_risk_decision(self, approved: bool, reasons: list[str]) -> None:
        """Add a risk decision message."""
        status = "APPROVED" if approved else "REJECTED"
        content = f"Risk Decision: {status}\nReasons: {', '.join(reasons) if reasons else 'None'}"
        self.add_message("risk", content, {"approved": approved, "reasons": reasons})

    def clear(self) -> None:
        """Clear all messages."""
        self._messages = []
        self.messages = self._messages
        self.refresh()

    def render(self) -> RenderableType:
        """Render the chat panel."""

        panel = Panel(
            self._render_messages(),
            title="Agent Chat",
            border_style="cyan",
            title_align="left",
        )
        return panel

    def _render_messages(self) -> RenderableType:
        """Render all messages."""
        if not self._messages:
            return Text("No messages yet. Start a conversation.", style="dim")

        renders: list[RenderableType] = []
        for msg in self._messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            role_color = {
                "user": "cyan",
                "agent": "green",
                "system": "blue",
                "tool": "yellow",
                "risk": "red",
            }.get(msg.role, "grey")

            role_label = Text(f"[{msg.role.upper()}] ", style=Style(color=role_color, bold=True))
            time_label = Text(f" {timestamp} ", style=Style(color="muted", dim=True))

            content_text = Text(msg.content, style="")
            renders.append(Text.assemble(role_label, time_label, "\n", content_text, "\n"))

        return Group(*renders)
