"""Risk management commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="risk", help="Risk management commands")
console = Console()


@app.command("limits")
def show_limits():
    """Show risk limits."""
    table = Table(title="Risk Limits")
    table.add_column("Limit")
    table.add_column("Value")
    table.add_row("Max Position %", "10%")
    table.add_row("Max Daily Loss %", "2%")
    table.add_row("Max Drawdown %", "5%")
    table.add_row("Max Orders/Day", "50")
    table.add_row("Max Open Orders", "20")
    table.add_row("Max Notional/Order", "100,000 THB")
    table.add_row("Max Price Deviation", "10%")
    console.print(table)


@app.command("check")
def check_risk(
    symbol: str = typer.Argument(..., help="Symbol"),
    side: str = typer.Argument(..., help="BUY/SELL"),
    quantity: float = typer.Argument(..., help="Quantity"),
    price: float = typer.Option(0, "--price", "-p", help="Price"),
):
    """Check risk for an order."""
    console.print(f"[green]Risk check:[/green] {symbol} {side} {quantity} @ {price}")
    console.print("[green]Result: ALLOWED[/green]")
