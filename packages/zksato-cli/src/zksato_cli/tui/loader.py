"""Loader animations for zksato TUI.

Provides spinner, gradient, and minimal loader animations for use while
waiting for LLM responses or tool execution.
"""

from __future__ import annotations

from rich.console import RenderableType
from rich.spinner import Spinner
from rich.style import Style
from rich.text import Text

# Braille dot animation frames
BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠶", "⠦", "⠧", "⠇", "⠏"]

# Dot animation frames
DOT_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴"]

MINIMAL_FRAMES = [".  ", ".. ", "...", "   "]


class Loader:
    """Loader animation for displaying while waiting."""

    def __init__(self, style: str = "spinner", text: str = "Loading...") -> None:
        self.style = style
        self.text = text
        self._frame_index = 0

    def frame(self) -> RenderableType:
        """Get the current frame of the animation."""
        if self.style == "spinner":
            return Spinner("dots", text=self.text, style="cyan")
        elif self.style == "gradient":
            return self._gradient_frame()
        elif self.style == "minimal":
            return Text(self._minimal_frame() + self.text, style="cyan")
        else:
            return Text(self.text, style="cyan")

    def _gradient_frame(self) -> Text:
        """Gradient color shimmer over the text."""
        colors = ["#00D4AA", "#7C3AED", "#3B82F6", "#F59E0B", "#EF4444"]
        color = colors[self._frame_index % len(colors)]
        self._frame_index += 1
        return Text(self.text, style=Style(color=color, bold=True))

    def _minimal_frame(self) -> str:
        """Trailing dots animation."""
        frame = MINIMAL_FRAMES[self._frame_index % len(MINIMAL_FRAMES)]
        self._frame_index += 1
        return frame

    def update(self) -> None:
        """Advance to the next frame."""
        self._frame_index = (self._frame_index + 1) % 10
