"""Configuration commands."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
import tomllib

from zksato_core.config import Settings, BaseConfig
from zksato_risk.policies.loader import PolicyLoader

app = typer.Typer(name="config", help="Configuration commands")
console = Console()


@app.command("show")
def show_config(
    env: str = typer.Option("dev", "--env", "-e", help="Environment (dev, test, uat, prod)"),
    show_secrets: bool = typer.Option(False, "--show-secrets", help="Show secret values (default: masked)"),
):
    """Show current configuration."""
    settings = Settings.load(env=env)
    
    table = Table(title=f"Configuration ({env})")
    table.add_column("Setting")
    table.add_column("Value")
    
    # App settings
    table.add_row("app_name", settings.app_name)
    table.add_row("environment", settings.environment)
    table.add_row("trading_mode", settings.trading_mode)
    table.add_row("live_trading_enabled", str(settings.live_trading_enabled))
    table.add_row("automation_enabled", str(settings.automation_enabled))
    table.add_row("dashboard_enabled", str(settings.dashboard_enabled))
    table.add_row("poll_interval_seconds", str(settings.poll_interval_seconds))
    table.add_row("initial_cash", f"{settings.initial_cash:,.2f}")
    
    # Database
    table.add_row("database_url", settings.database_url or "not set (in-memory)")
    table.add_row("redis_url", settings.redis_url or "not set")
    
    # Auth
    table.add_row("auth_required", str(settings.auth_required))
    if settings.api_keys and show_secrets:
        table.add_row("api_keys", settings.api_keys)
    elif settings.api_keys:
        table.add_row("api_keys", "[MASKED]")
    
    # Market
    table.add_row("market_data_stale_seconds", str(settings.market_data_stale_seconds))
    table.add_row("market_timezone", settings.market_timezone)
    table.add_row("equity_sessions", settings.equity_sessions)
    table.add_row("enforce_market_sessions", str(settings.enforce_market_sessions))
    table.add_row("strict_reference_data", str(settings.strict_reference_data))
    
    # Risk
    table.add_row("max_positions", str(settings.max_positions))
    table.add_row("max_position_pct", f"{settings.max_position_pct}%")
    table.add_row("max_risk_per_trade_pct", f"{settings.max_risk_per_trade_pct}%")
    table.add_row("max_daily_loss_pct", f"{settings.max_daily_loss_pct}%")
    table.add_row("max_drawdown_pct", f"{settings.max_drawdown_pct}%")
    table.add_row("max_orders_per_day", str(settings.max_orders_per_day))
    table.add_row("max_open_orders", str(settings.max_open_orders))
    table.add_row("max_notional_per_order", f"{settings.max_notional_per_order:,.2f}")
    table.add_row("max_price_deviation_pct", f"{settings.max_price_deviation_pct}%")
    table.add_row("max_gross_exposure_pct", f"{settings.max_gross_exposure_pct}%")
    table.add_row("max_net_exposure_pct", f"{settings.max_net_exposure_pct}%")
    table.add_row("max_symbol_exposure_pct", f"{settings.max_symbol_exposure_pct}%")
    table.add_row("max_sector_exposure_pct", f"{settings.max_sector_exposure_pct}%")
    table.add_row("max_spread_pct", f"{settings.max_spread_pct}%")
    table.add_row("require_stop_loss", str(settings.require_stop_loss))
    table.add_row("allow_equity_short_selling", str(settings.allow_equity_short_selling))
    table.add_row("kill_switch", str(settings.kill_switch))
    
    # Strategy (only if available)
    if hasattr(settings, 'default_strategy'):
        table.add_row("default_strategy", settings.default_strategy)
    if hasattr(settings, 'default_order_size'):
        table.add_row("default_order_size", str(settings.default_order_size))
    if hasattr(settings, 'default_stop_loss_pct'):
        table.add_row("default_stop_loss_pct", f"{settings.default_stop_loss_pct}%")
    if hasattr(settings, 'default_take_profit_pct'):
        table.add_row("default_take_profit_pct", f"{settings.default_take_profit_pct}%")
    if hasattr(settings, 'default_watchlist'):
        table.add_row("default_watchlist", settings.default_watchlist)
    
    console.print(table)


@app.command("validate")
def validate_config(
    env: str = typer.Option("dev", "--env", "-e", help="Environment (dev, test, uat, prod)"),
    config_file: Path = typer.Option(None, "--config", "-c", help="Path to config file"),
    policy_file: Path = typer.Option(None, "--policy", "-p", help="Path to policy file"),
):
    """Validate configuration and policies."""
    errors = []
    warnings = []
    
    # Validate main config
    try:
        if config_file:
            with config_file.open("rb") as f:
                data = tomllib.load(f)
            settings = Settings(**data)
        else:
            settings = Settings.load(env=env)
        
        # Additional validation
        if settings.trading_mode in {"live", "sandbox"} and not settings.database_url:
            errors.append("database_url is required for live/sandbox mode")
        
        if settings.trading_mode == "live" and not settings.auth_required:
            errors.append("auth_required must be true in live mode")
        
        if settings.auth_required and not settings.session_secret:
            warnings.append("session_secret should be set when auth_required is true")
        
        if settings.trading_mode != "paper" and not settings.settrade_configured:
            warnings.append("settrade credentials not configured for non-paper mode")
        
        if settings.trading_mode != "paper" and settings.reconciliation_enabled and not settings.database_url:
            errors.append("database_url required for reconciliation in non-paper mode")
        
    except Exception as e:
        errors.append(f"Config validation failed: {e}")
    
    # Validate policies
    if policy_file:
        try:
            loader = PolicyLoader(settings if 'settings' in locals() else Settings())
            policy_file_obj = loader.load(policy_file)
            policies = loader.create_policies(policy_file_obj)
            console.print(f"[green]Loaded {len(policies)} policies from {policy_file}[/green]")
        except Exception as e:
            errors.append(f"Policy validation failed: {e}")
    else:
        # Try default policy file
        default_policy = Path("config/policies/trading.toml")
        if default_policy.exists():
            try:
                loader = PolicyLoader(settings if 'settings' in locals() else Settings())
                policy_file_obj = loader.load(default_policy)
                policies = loader.create_policies(policy_file_obj)
                console.print(f"[green]Loaded {len(policies)} policies from default location[/green]")
            except Exception as e:
                warnings.append(f"Default policy file validation warning: {e}")
    
    # Print results
    if errors:
        console.print("[red]Validation FAILED:[/red]")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")
        raise typer.Exit(1)
    
    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")
    
    console.print("[green]Configuration valid![/green]")


@app.command("show-toml")
def show_toml(
    env: str = typer.Option("dev", "--env", "-e", help="Environment (dev, test, uat, prod)"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Show resolved TOML configuration."""
    settings = Settings.load(env=env)
    toml_str = settings.to_toml()
    
    if output:
        output.write_text(toml_str)
        console.print(f"[green]Written to {output}[/green]")
    else:
        syntax = Syntax(toml_str, "toml", theme="monokai", line_numbers=True)
        console.print(syntax)


@app.command("show-policies")
def show_policies(
    policy_file: Path = typer.Option("config/policies/trading.toml", "--file", "-f", help="Policy file path"),
):
    """Show loaded policies."""
    try:
        settings = Settings.load(env="dev")
        loader = PolicyLoader(settings)
        policy_file_obj = loader.load(policy_file)
        policies = loader.create_policies(policy_file_obj)
        
        table = Table(title=f"Policies ({len(policies)} loaded)")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Version")
        table.add_column("Decision")
        
        for policy in policies:
            table.add_row(policy.name, type(policy).__name__, policy.version, "REJECT/WARN/APPROVE")
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to load policies: {e}[/red]")
        raise typer.Exit(1)