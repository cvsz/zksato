"""Strategy commands."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="strategy", help="Strategy commands")
console = Console()


@app.command("list")
def list_strategies():
    """List available strategies."""
    table = Table(title="Available Strategies")
    table.add_column("Name")
    table.add_column("Description")
    strategies = [
        ("ema_cross", "EMA crossover strategy"),
        ("sma_cross", "SMA crossover strategy"),
        ("rsi_reversion", "RSI mean reversion"),
        ("bollinger_reversion", "Bollinger Bands reversion"),
        ("momentum", "Momentum strategy"),
        ("macd_cross", "MACD crossover"),
        ("breakout", "Breakout strategy"),
        ("scalp", "Scalping strategy"),
        ("swing", "Swing trading"),
        ("position", "Position trading"),
        ("vwap", "VWAP strategy"),
        ("stochastic", "Stochastic oscillator"),
        ("williams_r", "Williams %R"),
        ("atr_channel", "ATR channel"),
        ("stat_arb", "Statistical arbitrage"),
        ("tfex_spread", "TFEX spread trading"),
    ]
    for name, desc in strategies:
        table.add_row(name, desc)
    console.print(table)


@app.command("test")
def test_strategy(
    strategy: str = typer.Argument(..., help="Strategy name"),
    symbol: str = typer.Option("AOT", "--symbol", "-s", help="Symbol to test"),
):
    """Test a strategy."""
    console.print(f"[green]Testing strategy:[/green] {strategy} on {symbol}")
    console.print("[yellow]Not implemented yet[/yellow]")