"""Hook CLI commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from zksato_cli.hooks.framework import (
    HookEvent,
    HookManager,
    setup_builtin_hooks,
)

app = typer.Typer(name="hook", help="Hook management commands")
console = Console()


@app.command("list")
def list_hooks(
    event: str | None = typer.Option(None, "--event", "-e", help="Filter by event"),
    enabled_only: bool = typer.Option(True, "--enabled/--all", help="Show only enabled hooks"),
) -> None:
    """List registered hooks."""
    manager = HookManager()
    setup_builtin_hooks(manager)

    event_filter = HookEvent(event) if event else None
    hooks = manager.get_hooks(event_filter)

    if not hooks:
        console.print("[yellow]No hooks found[/yellow]")
        return

    if enabled_only:
        hooks = [h for h in hooks if h.enabled]

    table = Table(title="Registered Hooks")
    table.add_column("Hook ID")
    table.add_column("Name")
    table.add_column("Event")
    table.add_column("Priority")
    table.add_column("Enabled")
    table.add_column("Description")

    for hook in hooks:
        table.add_row(
            hook.hook_id[:12] + "...",
            hook.name,
            hook.event.value,
            hook.priority.name,
            "✓" if hook.enabled else "✗",
            hook.description[:50],
        )

    console.print(table)


@app.command("register")
def register_hook(
    event: str = typer.Argument(..., help="Event name"),
    handler: str = typer.Argument(..., help="Handler function (module:function)"),
    name: str = typer.Option("", "--name", "-n", help="Hook name"),
    description: str = typer.Option("", "--description", "-d", help="Hook description"),
    priority: str = typer.Option(
        "normal", "--priority", "-p", help="Priority (critical, high, normal, low, background)"
    ),
    timeout: float = typer.Option(30.0, "--timeout", "-t", help="Timeout in seconds"),
) -> None:
    """Register a custom hook (placeholder - requires module import)."""
    console.print("[yellow]Custom hook registration requires module import[/yellow]")
    console.print("Use the HookManager API directly in your code.")


@app.command("enable")
def enable_hook(
    hook_id: str = typer.Argument(..., help="Hook ID"),
) -> None:
    """Enable a hook."""
    manager = HookManager()
    setup_builtin_hooks(manager)

    if manager.enable_hook(hook_id):
        console.print(f"[green]Enabled hook:[/green] {hook_id}")
    else:
        console.print(f"[red]Hook not found:[/red] {hook_id}")


@app.command("disable")
def disable_hook(
    hook_id: str = typer.Argument(..., help="Hook ID"),
) -> None:
    """Disable a hook."""
    manager = HookManager()
    setup_builtin_hooks(manager)

    if manager.disable_hook(hook_id):
        console.print(f"[yellow]Disabled hook:[/yellow] {hook_id}")
    else:
        console.print(f"[red]Hook not found:[/red] {hook_id}")


@app.command("test")
def test_hook(
    event: str = typer.Argument(..., help="Event to test"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
    plan_id: str | None = typer.Option(None, "--plan", "-p", help="Plan ID"),
    task_id: str | None = typer.Option(None, "--task", "-t", help="Task ID"),
    data: str = typer.Option("{}", "--data", "-d", help="Event data (JSON)"),
) -> None:
    """Test hook execution for an event."""
    import json

    manager = HookManager()
    setup_builtin_hooks(manager)

    event_enum = HookEvent(event)
    context_data = json.loads(data)

    async def run():
        results = await manager.emit_simple(
            event_enum,
            session_id=session_id,
            plan_id=plan_id,
            task_id=task_id,
            data=context_data,
        )
        return results

    results = asyncio.run(run())

    console.print(f"[green]Executed {len(results)} hook(s) for {event}[/green]")
    for result in results:
        status_color = "green" if result.success else "red"
        console.print(
            f"  [{status_color}]{'✓' if result.success else '✗'}[/] "
            f"{result.hook_id[:12]}... ({result.duration_ms:.1f}ms)"
        )
        if result.error:
            console.print(f"    Error: {result.error}")


if __name__ == "__main__":
    app()
