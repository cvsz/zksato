"""TUI styling helpers for zksato.

Provides color palettes, text styles, and formatting helpers for the
terminal UI. All styles are designed to work on both dark and light
terminal themes.
"""

from __future__ import annotations

from rich.style import Style
from rich.text import Text

# Color palette using valid CSS color names
COLORS = {
    "primary": "cyan",
    "secondary": "magenta",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
    "muted": "gray70",
    "surface": "black",
    "surface_light": "gray70",
    "text": "white",
    "text_dim": "gray70",
}

# Risk level colors
RISK_COLORS = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
    "critical": "red",
}

# Trade side colors
SIDE_COLORS = {
    "buy": "green",
    "sell": "red",
    "short": "yellow",
}

# Order status colors
STATUS_COLORS = {
    "pending": "yellow",
    "open": "blue",
    "filled": "green",
    "cancelled": "gray70",
    "rejected": "red",
    "expired": "gray70",
}


def style_text(text: str, color: str, bold: bool = False) -> Text:
    """Create styled text with the given color."""
    style = Style(color=color, bold=bold)
    return Text(text, style=style)


def style_panel_title(text: str, color: str = "primary") -> Text:
    """Create styled panel title."""
    return Text(text, style=Style(color=color, bold=True))


def format_risk_level(level: str) -> Text:
    """Format risk level with appropriate color."""
    color = RISK_COLORS.get(level.lower(), COLORS["muted"])
    return Text(level.upper(), style=Style(color=color, bold=True))


def format_side(side: str) -> Text:
    """Format trade side with appropriate color."""
    color = SIDE_COLORS.get(side.lower(), COLORS["muted"])
    return Text(side.upper(), style=Style(color=color, bold=True))


def format_status(status: str) -> Text:
    """Format order/status with appropriate color."""
    color = STATUS_COLORS.get(status.lower(), COLORS["muted"])
    return Text(status.upper(), style=Style(color=color))


def format_number(value: float, decimals: int = 2, prefix: str = "") -> str:
    """Format a number with commas and optional prefix."""
    formatted = f"{value:,.{decimals}f}"
    if prefix:
        return f"{prefix}{formatted}"
    return formatted


def format_currency(value: float, currency: str = "THB") -> str:
    """Format a value as currency."""
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    return f"{sign}{currency} {abs_value:,.2f}"


def format_pct(value: float, decimals: int = 2) -> str:
    """Format a percentage value."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"
