"""Plan mode CLI commands."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zksato_cli.planning.plan_mode import (
    Plan,
    PlanManager,
    PlanPhase,
    PlanStore,
    TaskStatus,
)
from zksato_cli.sessions.persistence import SessionManager

app = typer.Typer(name="plan", help="Plan mode commands")
console = Console()


@app.command("create")
def create_plan(
    objective: str = typer.Argument(..., help="Plan objective"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
    files: list[str] | None = typer.Option(None, "--file", "-f", help="Files to explore"),
) -> None:
    """Create a new exploration plan."""
    session_manager = SessionManager(".zksato/sessions")
    plan_manager = PlanManager(Path(project_root), session_manager, storage_dir)

    # Create or use session
    if session_id:
        session = session_manager.get_session(session_id)
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            return
    else:
        session = session_manager.create_session(project_root, f"Plan: {objective[:50]}")

    plan = plan_manager.create_exploration_plan(objective, session.session_id, files)
    console.print(f"[green]Created exploration plan:[/green] {plan.plan_id}")
    console.print(f"  Objective: {objective}")
    console.print(f"  Session: {session.session_id}")
    console.print(f"  Tasks: {len(plan.tasks)}")


@app.command("list")
def list_plans(
    session_id: str | None = typer.Option(None, "--session", "-s", help="Filter by session"),
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum plans to show"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """List plans."""
    store = PlanStore(storage_dir)

    status_filter = PlanPhase(status) if status else None
    plans = store.list_plans(session_id, status_filter, limit)

    if not plans:
        console.print("[yellow]No plans found[/yellow]")
        return

    table = Table(title="Plans")
    table.add_column("Plan ID")
    table.add_column("Session")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Phase")
    table.add_column("Progress")
    table.add_column("Tasks")

    for p in plans:
        table.add_row(
            p["plan_id"][:12] + "...",
            p["session_id"][:12] + "...",
            p["title"][:30],
            p["status"],
            p["current_phase"],
            f"{p['progress'] * 100:.0f}%",
            f"{p['completed_tasks']}/{p['task_count']}",
        )

    console.print(table)


@app.command("show")
def show_plan(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
    show_tasks: bool = typer.Option(True, "--tasks/--no-tasks", help="Show tasks"),
) -> None:
    """Show plan details."""
    store = PlanStore(storage_dir)
    plan = store.load_plan(plan_id)

    if not plan:
        console.print(f"[red]Plan not found: {plan_id}[/red]")
        return

    console.print(f"[bold]Plan:[/bold] {plan.plan_id}")
    console.print(f"  Session: {plan.session_id}")
    console.print(f"  Title: {plan.title}")
    console.print(f"  Objective: {plan.objective}")
    console.print(f"  Status: {plan.status.value}")
    console.print(f"  Phase: {plan.current_phase.value}")
    console.print(f"  Progress: {plan.progress() * 100:.0f}%")
    console.print(f"  Read-only: {plan.read_only_mode}")
    console.print(f"  Tasks: {len(plan.tasks)}")
    console.print(f"  Completed: {sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)}")
    console.print(f"  Failed: {sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)}")

    if show_tasks and plan.tasks:
        console.print("\n[bold]Tasks:[/bold]")
        for task in plan.tasks:
            status_color = {
                TaskStatus.PENDING: "yellow",
                TaskStatus.READY: "cyan",
                TaskStatus.RUNNING: "blue",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.SKIPPED: "dim",
                TaskStatus.BLOCKED: "red",
            }.get(task.status, "white")
            console.print(
                f"  [{status_color}]{task.status.value}[/] {task.task_type.value}: {task.title}"
            )
            if task.dependencies:
                console.print(f"    depends on: {', '.join(task.dependencies[:3])}")

    # Show approval gates
    if plan.approval_gates:
        console.print("\n[bold]Approval Gates:[/bold]")
        for gate in plan.approval_gates:
            console.print(f"  {gate.phase.value}: {gate.name} ({gate.status.value})")


@app.command("execute")
def execute_plan(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    auto_approve: bool = typer.Option(False, "--auto-approve", help="Auto-approve all gates"),
) -> None:
    """Execute a plan."""
    session_manager = SessionManager(".zksato/sessions")
    plan_manager = PlanManager(Path(project_root), session_manager, storage_dir)

    plan = plan_manager.load_plan(plan_id)
    if not plan:
        console.print(f"[red]Plan not found: {plan_id}[/red]")
        return

    console.print(f"[green]Executing plan:[/green] {plan.title}")

    async def approval_callback(item):
        if auto_approve:
            return True
        if hasattr(item, "title"):  # Task
            return typer.confirm(f"Approve task: {item.title}?")
        else:  # Gate
            return typer.confirm(f"Approve gate: {item.name}?")

    result = asyncio.run(plan_manager.execute_plan(plan, approval_callback))

    console.print(f"\n[bold]Execution complete:[/bold] {result.status.value}")
    if result.has_failures():
        console.print("[red]Some tasks failed:[/red]")
        for task in result.get_failed_tasks():
            console.print(f"  {task.title}: {task.error}")


@app.command("approve")
def approve_gate(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    phase: str = typer.Argument(
        ...,
        help="Phase to approve (discover, analyze, plan, approve, execute, review, verify, complete)",
    ),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """Approve a plan gate."""
    store = PlanStore(storage_dir)
    plan = store.load_plan(plan_id)

    if not plan:
        console.print(f"[red]Plan not found: {plan_id}[/red]")
        return

    phase_enum = PlanPhase(phase)
    gate = plan.get_approval_gate(phase_enum)

    if not gate:
        console.print(f"[yellow]No approval gate for phase: {phase}[/yellow]")
        return

    if gate.status != "pending":
        console.print(f"[yellow]Gate already {gate.status.value}[/yellow]")
        return

    gate.status = "approved"
    gate.decided_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    store.save_plan(plan)

    console.print(f"[green]Approved gate:[/green] {gate.name}")


@app.command("reject")
def reject_gate(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    phase: str = typer.Argument(..., help="Phase to reject"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """Reject a plan gate."""
    store = PlanStore(storage_dir)
    plan = store.load_plan(plan_id)

    if not plan:
        console.print(f"[red]Plan not found: {plan_id}[/red]")
        return

    phase_enum = PlanPhase(phase)
    gate = plan.get_approval_gate(phase_enum)

    if not gate:
        console.print(f"[yellow]No approval gate for phase: {phase}[/yellow]")
        return

    gate.status = "rejected"
    gate.decided_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    gate.reason = reason
    store.save_plan(plan)

    console.print(f"[red]Rejected gate:[/red] {gate.name}")


@app.command("delete")
def delete_plan(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """Delete a plan."""
    if not force:
        confirm = typer.confirm(f"Delete plan {plan_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    store = PlanStore(storage_dir)
    if store.delete_plan(plan_id):
        console.print(f"[green]Deleted plan:[/green] {plan_id}")
    else:
        console.print(f"[red]Plan not found:[/red] {plan_id}")


@app.command("export")
def export_plan(
    plan_id: str = typer.Argument(..., help="Plan ID"),
    output: str = typer.Argument(..., help="Output file path"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """Export plan to JSON file."""
    store = PlanStore(storage_dir)
    plan = store.load_plan(plan_id)

    if not plan:
        console.print(f"[red]Plan not found: {plan_id}[/red]")
        return

    with Path(output).open("w") as f:
        import json

        json.dump(plan.to_dict(), f, indent=2)

    console.print(f"[green]Exported plan to:[/green] {output}")


@app.command("import")
def import_plan(
    input_file: str = typer.Argument(..., help="Input file path"),
    storage_dir: str = typer.Option(".zksato/plans", "--storage", help="Plan storage directory"),
) -> None:
    """Import plan from JSON file."""
    store = PlanStore(storage_dir)

    with Path(input_file).open("r") as f:
        import json

        data = json.load(f)

    plan = Plan.from_dict(data)
    store.save_plan(plan)

    console.print(f"[green]Imported plan:[/green] {plan.plan_id}")


if __name__ == "__main__":
    app()
