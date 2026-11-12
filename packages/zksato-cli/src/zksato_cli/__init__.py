"""zksato-cli: CLI commands for zksato."""

from zksato_cli.main import app as cli_app
from zksato_cli.commands import bot, strategy, risk, broker, portfolio, agent, config

__version__ = "2.0.0-dev"

__all__ = [
    "cli_app",
    "bot",
    "strategy",
    "risk",
    "broker",
    "portfolio",
    "agent",
    "config",
]