"""Input panel component for zksato TUI.

Provides text input for user messages with different styles:
- block: Full-width background-colored input box
- bordered: Horizontal line frame
- plain: Simple readline prompt
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input


class InputSubmitted(Message):
    """Posted when the user submits input."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__()


class InputPanel(Widget):
    """Text input panel for user messages."""

    DEFAULT_CSS = """
    InputPanel {
        height: 3;
        border: solid cyan;
        padding: 0 1;
    }
    """

    input_style: reactive[str] = reactive("block")

    def __init__(self, input_style: str = "block", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_style = input_style
        self._input: Input | None = None

    def compose(self) -> Iterable[Input]:
        """Compose the input widget."""
        self._input = Input(placeholder="Type a command (e.g., /quote AAPL)...")
        yield self._input

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.post_message(InputSubmitted(event.value))
        if self._input is not None:
            self._input.value = ""

    def set_text(self, text: str) -> None:
        """Set the input text."""
        if self._input:
            self._input.value = text

    def clear(self) -> None:
        """Clear the input text."""
        if self._input is not None:
            self._input.value = ""

    def get_text(self) -> str:
        """Get the current input text."""
        if self._input:
            return self._input.value
        return ""

    def focus(self, scroll_visible: bool = False) -> InputPanel:
        """Focus the input widget."""
        if self._input:
            self._input.focus(scroll_visible)
        return self
