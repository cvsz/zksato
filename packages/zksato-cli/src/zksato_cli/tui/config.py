"""TUI configuration for zksato.

Handles display styles, loader animations, banner settings, and API connection
configuration for the terminal UI.
"""

from __future__ import annotations

from dataclasses import dataclass


class ToolDisplayStyle(str):
    """Tool call display style options."""

    EMOJI = "emoji"
    GROUPED = "grouped"
    MINIMAL = "minimal"
    HIDDEN = "hidden"


class InputStyle(str):
    """Input prompt style options."""

    BLOCK = "block"
    BORDERED = "bordered"
    PLAIN = "plain"


class LoaderStyle(str):
    """Loader animation style options."""

    SPINNER = "spinner"
    GRADIENT = "gradient"
    MINIMAL = "minimal"


@dataclass
class TUIConfig:
    """Configuration for the zksato TUI."""

    # API connection
    api_base_url: str = "http://localhost:9569"
    api_timeout: float = 30.0
    api_key: str | None = None

    # Display settings
    tool_display: ToolDisplayStyle = ToolDisplayStyle.GROUPED
    input_style: InputStyle = InputStyle.BLOCK
    loader_style: LoaderStyle = LoaderStyle.SPINNER

    # Banner
    show_banner: bool = True
    banner_text: str = "zksato"

    # Session
    session_id: str | None = None
    auto_save_session: bool = True

    # Risk/safety
    require_stop_loss: bool = True
    default_trading_mode: str = "paper"

    # Feature flags
    enable_market_data: bool = True
    enable_risk_display: bool = True
    enable_portfolio_display: bool = True
    enable_agent_chat: bool = True

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        return {
            "api_base_url": self.api_base_url,
            "api_timeout": self.api_timeout,
            "tool_display": self.tool_display.value,
            "input_style": self.input_style.value,
            "loader_style": self.loader_style.value,
            "show_banner": self.show_banner,
            "banner_text": self.banner_text,
            "session_id": self.session_id,
            "auto_save_session": self.auto_save_session,
            "require_stop_loss": self.require_stop_loss,
            "default_trading_mode": self.default_trading_mode,
            "enable_market_data": self.enable_market_data,
            "enable_risk_display": self.enable_risk_display,
            "enable_portfolio_display": self.enable_portfolio_display,
            "enable_agent_chat": self.enable_agent_chat,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TUIConfig:
        """Create config from dictionary."""
        return cls(
            api_base_url=data.get("api_base_url", "http://localhost:9569"),
            api_timeout=data.get("api_timeout", 30.0),
            api_key=data.get("api_key"),
            tool_display=ToolDisplayStyle(data.get("tool_display", "grouped")),
            input_style=InputStyle(data.get("input_style", "block")),
            loader_style=LoaderStyle(data.get("loader_style", "spinner")),
            show_banner=data.get("show_banner", True),
            banner_text=data.get("banner_text", "zksato"),
            session_id=data.get("session_id"),
            auto_save_session=data.get("auto_save_session", True),
            require_stop_loss=data.get("require_stop_loss", True),
            default_trading_mode=data.get("default_trading_mode", "paper"),
            enable_market_data=data.get("enable_market_data", True),
            enable_risk_display=data.get("enable_risk_display", True),
            enable_portfolio_display=data.get("enable_portfolio_display", True),
            enable_agent_chat=data.get("enable_agent_chat", True),
        )
