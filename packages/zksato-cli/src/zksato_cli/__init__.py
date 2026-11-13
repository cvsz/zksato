"""zksato-cli: CLI commands for zksato."""

from zksato_cli.commands import agent, bot, broker, config, portfolio, risk, strategy
from zksato_cli.main import app as cli_app

__version__ = "2.0.0-dev"

__all__ = [
    "agent",
    "bot",
    "broker",
    "cli_app",
    "config",
    "portfolio",
    "risk",
    "strategy",
]
