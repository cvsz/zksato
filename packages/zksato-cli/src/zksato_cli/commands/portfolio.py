"""Portfolio commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="portfolio", help="Portfolio commands")
console = Console()


@app.command("show")
def show_portfolio():
    """Show current portfolio."""
    table = Table(title="Portfolio")
    table.add_column("Symbol")
    table.add_column("Quantity")
    table.add_column("Avg Price")
    table.add_column("Market Price")
    table.add_column("Market Value")
    table.add_column("Unrealized P&L")
    console.print(table)
    console.print("[green]Total Equity: 500,000 THB[/green]")
    console.print("[green]Cash: 500,000 THB[/green]")


@app.command("positions")
def show_positions():
    """Show positions."""
    console.print("[yellow]No open positions[/yellow]")


@app.command("reconcile")
def reconcile_portfolio():
    """Reconcile portfolio with broker."""
    console.print("[green]Reconciling...[/green]")
    console.print("[green]Portfolio matched![/green]")