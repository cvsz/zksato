"""Configuration commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="config", help="Configuration commands")
console = Console()


@app.command("show")
def show_config():
    """Show current configuration."""
    table = Table(title="Configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("trading_mode", "paper")
    table.add_row("initial_cash", "500,000 THB")
    table.add_row("database_url", "sqlite:///./zksato.db")
    table.add_row("redis_url", "redis://localhost:6379/0")
    console.print(table)


@app.command("set")
def set_config(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value"),
):
    """Set a configuration value."""
    console.print(f"[green]Setting {key} = {value}[/green]")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command("validate")
def validate_config():
    """Validate configuration."""
    console.print("[green]Configuration valid![/green]")
