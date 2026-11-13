"""TUI command for zksato CLI.

Launches the terminal user interface for agent management.
"""

import typer
from rich.console import Console
from rich.table import Table

from zksato_cli.tui.app import ZKSATOTUI
from zksato_cli.tui.config import (
    InputStyle,
    LoaderStyle,
    ToolDisplayStyle,
    TUIConfig,
)

app = typer.Typer(name="tui", help="Terminal UI for agent management")
console = Console()


@app.command()
def start(
    *,
    host: str = typer.Option("localhost", "--host", "-h", help="API host"),
    port: int = typer.Option(9569, "--port", "-p", help="API port"),
    api_key: str = typer.Option(None, "--api-key", "-k", help="API key"),
    thinking: str = typer.Option(
        "high", "--thinking", "-t", help="Thinking level (low/medium/high/xhigh)"
    ),
    input_style: str = typer.Option(
        "block", "--input", "-i", help="Input style (block/bordered/plain)"
    ),
    tool_display: str = typer.Option(
        "grouped", "--tool-display", "-d", help="Tool display style (emoji/grouped/minimal)"
    ),
    loader: str = typer.Option(
        "spinner", "--loader", "-l", help="Loader style (spinner/gradient/minimal)"
    ),
    banner: str = typer.Option("zksato", "--banner", "-b", help="Banner text"),
    no_banner: bool = typer.Option(False, "--no-banner", help="Disable banner"),
) -> None:
    """Launch the zksato terminal UI."""
    console.print("[green]Starting zksato TUI[/green]")
    console.print(f"  API: {host}:{port}")
    console.print(f"  Thinking: {thinking}")
    console.print(f"  Input style: {input_style}")
    console.print(f"  Tool display: {tool_display}")
    console.print(f"  Loader: {loader}")

    config = TUIConfig(
        api_base_url=f"http://{host}:{port}",
        api_key=api_key if api_key else None,
        tool_display=ToolDisplayStyle(tool_display),
        input_style=InputStyle(input_style),
        loader_style=LoaderStyle(loader),
        show_banner=not no_banner,
        banner_text=banner,
    )

    app = ZKSATOTUI(config=config)
    app.run()


@app.command()
def list_styles() -> None:
    """List available display styles."""
    table = Table(title="Available Styles")
    table.add_column("Setting")
    table.add_column("Options")

    table.add_row("Input style", "block, bordered, plain")
    table.add_row("Tool display", "emoji, grouped, minimal")
    table.add_row("Loader", "spinner, gradient, minimal")

    console.print(table)
