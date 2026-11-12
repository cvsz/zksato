"""Main CLI application for zksato."""

import typer
from rich.console import Console

from zksato_cli.commands import bot, strategy, risk, broker, portfolio, agent, config

app = typer.Typer(
    name="zksato",
    help="zksato automated trading platform CLI",
    no_args_is_help=True,
)

console = Console()

app.add_typer(bot.app, name="bot", help="Bot management commands")
app.add_typer(strategy.app, name="strategy", help="Strategy commands")
app.add_typer(risk.app, name="risk", help="Risk management commands")
app.add_typer(broker.app, name="broker", help="Broker commands")
app.add_typer(portfolio.app, name="portfolio", help="Portfolio commands")
app.add_typer(agent.app, name="agent", help="Agent commands")
app.add_typer(config.app, name="config", help="Configuration commands")


@app.callback()
def main():
    """zksato CLI - Automated trading platform for SET/TFEX."""


if __name__ == "__main__":
    app()