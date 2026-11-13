"""Tool panel component for zksato TUI.

Displays tool execution results with different display styles:
- emoji: Per-call markers with tool name, arguments, and timing
- grouped: Bold action labels with tree-branch output
- minimal: Aggregated one-liner summaries
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


class ToolPanel(Widget):
    """Tool execution display panel."""

    DEFAULT_CSS = """
    ToolPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1;
    }
    """

    tool_calls: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, tool_display: str = "grouped", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tool_calls: list[dict[str, Any]] = []
        self.tool_display = tool_display

    def add_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
        result: str | None = None,
        status: str = "pending",
    ) -> None:
        """Add a tool call to the display."""
        entry: dict[str, Any] = {
            "tool": tool_name,
            "args": args or {},
            "result": result,
            "status": status,
            "timestamp": datetime.now(),
        }
        self._tool_calls.append(entry)
        self.tool_calls = self._tool_calls
        self.refresh()

    def update_tool_result(self, tool_name: str, result: str) -> None:
        """Update the result of the most recent tool call."""
        for entry in reversed(self._tool_calls):
            if entry["tool"] == tool_name and entry["status"] == "pending":
                entry["result"] = result
                entry["status"] = "completed"
                break
        self.tool_calls = self._tool_calls
        self.refresh()

    def clear(self) -> None:
        """Clear all tool calls."""
        self._tool_calls = []
        self.tool_calls = []
        self.refresh()

    def render(self) -> RenderableType:
        """Render the tool panel."""
        if not self._tool_calls:
            return Panel(
                "No tool calls yet.",
                title="Tool Execution",
                border_style="cyan",
                title_align="left",
            )

        renders: list[RenderableType] = [
            self._render_tool_entry(entry) for entry in self._tool_calls
        ]

        return Panel(
            Group(*renders),
            title="Tool Execution",
            border_style="cyan",
            title_align="left",
        )

    def _render_tool_entry(self, entry: dict[str, Any]) -> Text:
        """Render a single tool call entry."""
        tool_name = entry["tool"]
        status = entry["status"]
        result = entry.get("result")

        status_color = {
            "pending": "warning",
            "completed": "success",
            "error": "error",
        }.get(status, "muted")

        if self.tool_display == "emoji":
            tool_emoji = {
                "get_quote": "📊",
                "place_order": "💰",
                "get_positions": "📈",
                "cancel_order": "❌",
                "check_risk": "🛡️",
                "get_market_health": "🏥",
            }.get(tool_name, "🔧")

            text = Text.assemble(
                Text(f"{tool_emoji} ", style=""),
                Text(tool_name, style=Style(color="cyan", bold=True)),
                Text(f" [{status}] ", style=Style(color=status_color, bold=True)),
                "\n",
            )
            if entry.get("args"):
                text.append(Text(f"  Args: {entry['args']}\n", style="dim"))
            if result:
                text.append(Text(f"  Result: {result}\n", style="green"))
            return text

        elif self.tool_display == "minimal":
            text = Text.assemble(
                Text(f"[{tool_name}] ", style=Style(color="cyan", bold=True)),
                Text(f"{status} ", style=Style(color=status_color)),
            )
            if result:
                text.append(Text(f"→ {result}", style="green"))
            return text

        else:  # grouped
            text = Text.assemble(
                Text(f"▸ {tool_name}", style=Style(color="cyan", bold=True)),
                Text(f" [{status}] ", style=Style(color=status_color, bold=True)),
                "\n",
            )
            if entry.get("args"):
                args_str = ", ".join(f"{k}={v}" for k, v in entry["args"].items())
                text.append(Text(f"  args: {args_str}\n", style="dim"))
            if result:
                text.append(Text(f"  result: {result}\n", style="green"))
            return text
