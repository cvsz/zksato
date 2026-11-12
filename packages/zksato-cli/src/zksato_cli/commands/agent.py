"""Agent commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="agent", help="Agent commands")
console = Console()


@app.command("start")
def start_agent(
    name: str = typer.Argument(..., help="Agent name"),
    subaccount: str = typer.Option("default", "--subaccount", "-s", help="Sub-account"),
):
    """Start an agent."""
    console.print(f"[green]Starting agent:[/green] {name} (subaccount: {subaccount})")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command("stop")
def stop_agent(name: str = typer.Argument(..., help="Agent name")):
    """Stop an agent."""
    console.print(f"[red]Stopping agent:[/red] {name}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command("list")
def list_agents():
    """List agents."""
    console.print("[yellow]No agents running[/yellow]")


@app.command("skills")
def list_skills():
    """List available skills."""
    table = Table(title="Available Skills")
    table.add_column("Name")
    table.add_column("Description")
    skills = [
        ("get_quote", "Get real-time quote"),
        ("place_order", "Place an order"),
        ("get_positions", "Get positions"),
        ("cancel_order", "Cancel an order"),
        ("check_risk", "Check risk"),
    ]
    for name, desc in skills:
        table.add_row(name, desc)
    console.print(table)