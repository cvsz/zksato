"""Session management CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zksato_cli.sessions.persistence import SessionManager, SessionStatus

app = typer.Typer(name="session", help="Session management commands")
console = Console()


@app.command("create")
def create_session(
    project_path: str = typer.Argument(".", help="Project directory"),
    title: str = typer.Option("", "--title", "-t", help="Session title"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Create a new session."""
    manager = SessionManager(storage_dir)
    session = manager.create_session(project_path, title)
    console.print(f"[green]Created session:[/green] {session.session_id}")
    console.print(f"  Project: {session.project_path}")
    console.print(f"  Title: {session.title}")


@app.command("list")
def list_sessions(
    project_path: str | None = typer.Option(None, "--project", "-p", help="Filter by project path"),
    status: str | None = typer.Option(
        None, "--status", "-s", help="Filter by status (active, paused, completed, archived, error)"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum sessions to show"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """List sessions."""
    manager = SessionManager(storage_dir)

    status_filter = SessionStatus(status) if status else None
    sessions = manager.list_sessions(project_path, status_filter, limit)

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return

    table = Table(title="Sessions")
    table.add_column("Session ID")
    table.add_column("Project")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Messages")
    table.add_column("Tools")
    table.add_column("Last Activity")

    for s in sessions:
        table.add_row(
            s["session_id"][:12] + "...",
            s["project_path"],
            s["title"][:30],
            s["status"],
            str(s["message_count"]),
            str(s["tool_call_count"]),
            s["last_activity"][:19].replace("T", " "),
        )

    console.print(table)


@app.command("show")
def show_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
    messages: int = typer.Option(10, "--messages", "-m", help="Number of recent messages to show"),
) -> None:
    """Show session details."""
    manager = SessionManager(storage_dir)
    session = manager.get_session(session_id)

    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    console.print(f"[bold]Session:[/bold] {session.session_id}")
    console.print(f"  Project: {session.project_path}")
    console.print(f"  Title: {session.title}")
    console.print(f"  Status: {session.status.value}")
    console.print(f"  Created: {session.created_at.isoformat()}")
    console.print(f"  Updated: {session.updated_at.isoformat()}")
    console.print(f"  Messages: {session.get_message_count()}")
    console.print(f"  Tool calls: {session.get_tool_call_count()}")
    console.print(f"  Checkpoints: {len(session.checkpoints)}")
    console.print(f"  Tokens: {session.total_tokens}")
    console.print(f"  Cost: ${session.total_cost:.4f}")

    if messages > 0 and session.messages:
        console.print(f"\n[bold]Recent messages ({min(messages, len(session.messages))}):[/bold]")
        for msg in session.messages[-messages:]:
            role_color = {
                "user": "cyan",
                "assistant": "green",
                "system": "blue",
                "tool": "yellow",
                "tool_result": "magenta",
            }.get(msg.role.value, "white")
            console.print(f"  [{role_color}]{msg.role.value.upper()}[/]: {msg.content[:80]}...")
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    console.print(f"    Tool: {tc.name} ({tc.status})")


@app.command("resume")
def resume_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Resume a previous session."""
    manager = SessionManager(storage_dir)
    session = manager.resume_session(session_id)

    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    console.print(f"[green]Resumed session:[/green] {session.session_id}")
    console.print(f"  Title: {session.title}")
    console.print(f"  Messages: {session.get_message_count()}")
    console.print(f"  Last activity: {session.last_activity.isoformat()}")


@app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Delete a session."""
    if not force:
        confirm = typer.confirm(f"Delete session {session_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    manager = SessionManager(storage_dir)
    if manager.delete_session(session_id):
        console.print(f"[green]Deleted session:[/green] {session_id}")
    else:
        console.print(f"[red]Session not found:[/red] {session_id}")


@app.command("archive")
def archive_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Archive a session."""
    manager = SessionManager(storage_dir)
    if manager.store.archive_session(session_id):
        console.print(f"[green]Archived session:[/green] {session_id}")
    else:
        console.print(f"[red]Session not found:[/red] {session_id}")


@app.command("recover")
def recover_sessions(
    project_path: str | None = typer.Option(None, "--project", "-p", help="Project directory"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Recover interrupted sessions."""
    manager = SessionManager(storage_dir)
    recovered = manager.store.recover_interrupted_sessions(project_path)

    if not recovered:
        console.print("[green]No interrupted sessions found[/green]")
        return

    console.print(f"[yellow]Found {len(recovered)} interrupted session(s):[/yellow]")
    for session in recovered:
        console.print(
            f"  {session.session_id} - {session.title} (last: {session.last_activity.isoformat()})"
        )


@app.command("export")
def export_session(
    session_id: str = typer.Argument(..., help="Session ID"),
    output: str = typer.Argument(..., help="Output file path"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Export session to portable JSON file."""
    manager = SessionManager(storage_dir)
    if manager.export_session(session_id, Path(output)):
        console.print(f"[green]Exported session to:[/green] {output}")
    else:
        console.print(f"[red]Session not found:[/red] {session_id}")


@app.command("import")
def import_session(
    input_file: str = typer.Argument(..., help="Input file path"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Import session from portable JSON file."""
    manager = SessionManager(storage_dir)
    session = manager.import_session(Path(input_file))
    if session:
        console.print(f"[green]Imported session:[/green] {session.session_id}")
        console.print(f"  Title: {session.title}")
    else:
        console.print("[red]Failed to import session[/red]")


@app.command("checkpoint")
def create_checkpoint(
    session_id: str = typer.Argument(..., help="Session ID"),
    label: str = typer.Argument(..., help="Checkpoint label"),
    description: str = typer.Option("", "--description", "-d", help="Checkpoint description"),
    storage_dir: str = typer.Option(
        ".zksato/sessions", "--storage", help="Session storage directory"
    ),
) -> None:
    """Create a checkpoint for a session."""
    manager = SessionManager(storage_dir)
    session = manager.get_session(session_id)

    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    session.checkpoints[-1] if session.checkpoints else None

    session.checkpoints.append(
        # Create checkpoint directly since we don't have state_snapshot here
        # In practice, this would be called from the agent with actual state
    )
    # This is a simplified version - real usage would be from agent
    console.print("[yellow]Checkpoint creation requires state snapshot from agent[/yellow]")


if __name__ == "__main__":
    app()
