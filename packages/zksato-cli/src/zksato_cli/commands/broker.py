"""Broker commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="broker", help="Broker commands")
console = Console()


@app.command("list")
def list_brokers():
    """List available brokers."""
    table = Table(title="Available Brokers")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_row("paper", "Paper Trading", "active")
    table.add_row("settrade", "SET Equity", "inactive")
    table.add_row("ccxt", "Crypto (Binance, etc.)", "inactive")
    console.print(table)


@app.command("connect")
def connect_broker(
    name: str = typer.Argument(..., help="Broker name"),
):
    """Connect to a broker."""
    console.print(f"[green]Connecting to broker:[/green] {name}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command("orders")
def list_orders(
    broker: str = typer.Option("paper", "--broker", "-b", help="Broker name"),
    status: str = typer.Option("open", "--status", "-s", help="Order status"),
):
    """List orders."""
    console.print(f"[green]Orders from {broker}:[/green] status={status}")
    console.print("[yellow]Not implemented yet[/yellow]")
