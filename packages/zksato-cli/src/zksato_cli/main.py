"""Main CLI application for zksato."""

import typer
from rich.console import Console

from zksato_cli.commands import (
    agent,
    bot,
    broker,
    config,
    context,
    edit,
    git,
    hook,
    mcp,
    plan,
    portfolio,
    risk,
    session,
    skill,
    strategy,
    tui,
)

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
app.add_typer(edit.app, name="edit", help="File editing and search commands")
app.add_typer(context.app, name="context", help="Context management commands")
app.add_typer(git.app, name="git", help="Git integration commands")
app.add_typer(hook.app, name="hook", help="Hook management commands")
app.add_typer(mcp.app, name="mcp", help="MCP (Model Context Protocol) commands")
app.add_typer(plan.app, name="plan", help="Plan mode commands")
app.add_typer(skill.app, name="skill", help="Skill management commands")
app.add_typer(session.app, name="session", help="Session management commands")
app.add_typer(tui.app, name="tui", help="Terminal UI for agent management")


@app.callback()
def main() -> None:
    """zksato CLI - Automated trading platform for SET/TFEX."""


if __name__ == "__main__":
    app()
