"""Context management CLI commands."""

import json
from pathlib import Path

import typer
from rich.console import Console

from zksato_cli.context.manager import ContextManager, ContextSerializer

app = typer.Typer(name="context", help="Context management commands")
console = Console()


@app.command("create")
def create_context(
    context_id: str = typer.Argument(..., help="Context ID"),
    objective: str = typer.Option("", "--objective", "-o", help="Task objective"),
    files: list[str] | None = typer.Option(
        None, "--file", "-f", help="Repository files to include"
    ),
    max_tokens: int = typer.Option(100000, "--max-tokens", "-m", help="Maximum tokens"),
) -> None:
    """Create a new context."""
    manager = ContextManager()
    ctx = manager.create_task_context(context_id, objective, files, max_tokens)
    console.print(f"[green]Created context:[/green] {context_id}")
    console.print(f"  Objective: {objective}")
    console.print(f"  Files: {len(files) if files else 0}")
    console.print(f"  Tokens: {ctx.used_tokens}/{ctx.max_tokens}")


@app.command("show")
def show_context(
    context_id: str = typer.Argument(..., help="Context ID"),
) -> None:
    """Show context details."""
    manager = ContextManager()
    ctx = manager.get_context(context_id)

    if not ctx.entries:
        console.print(f"[yellow]Context empty:[/yellow] {context_id}")
        return

    console.print(f"[bold]Context:[/bold] {context_id}")
    console.print(f"  Entries: {len(ctx.entries)}")
    console.print(f"  Tokens: {ctx.used_tokens}/{ctx.max_tokens}")
    console.print(f"  Available: {ctx.available_tokens}")

    sources = {}
    for entry in ctx.entries:
        sources[entry.source] = sources.get(entry.source, 0) + 1
    console.print(f"  Sources: {dict(sources)}")

    console.print("\n[bold]Recent entries:[/bold]")
    for entry in ctx.entries[-5:]:
        preview = entry.content[:80].replace("\n", " ")
        console.print(f"  [{entry.source}] {preview}...")


@app.command("add")
def add_to_context(
    context_id: str = typer.Argument(..., help="Context ID"),
    content: str = typer.Argument(..., help="Content to add"),
    source: str = typer.Option("user", "--source", "-s", help="Source (user, agent, tool, file)"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t", help="Tags"),
) -> None:
    """Add content to context."""
    manager = ContextManager()

    if source == "file":
        # Read from file
        content = Path(content).read_text(encoding="utf-8")
        manager.add_file_content(context_id, content, content)
    else:
        manager.add_user_input(context_id, content)

    console.print(f"[green]Added to context:[/green] {context_id}")


@app.command("compact")
def compact_context(
    context_id: str = typer.Argument(..., help="Context ID"),
    target: int | None = typer.Option(None, "--target", "-t", help="Target tokens"),
    strategy: str = typer.Option(
        "importance", "--strategy", "-s", help="Strategy (importance, recency, size)"
    ),
) -> None:
    """Compact context to fit token budget."""
    manager = ContextManager()
    ctx = manager.get_context(context_id)

    removed = ctx.compact(target, strategy)
    console.print(f"[green]Compacted:[/green] removed {removed} entries")
    console.print(f"  Tokens: {ctx.used_tokens}/{ctx.max_tokens}")


@app.command("summarize")
def summarize_context(
    context_id: str = typer.Argument(..., help="Context ID"),
) -> None:
    """Generate a summary of the context."""
    manager = ContextManager()
    ctx = manager.get_context(context_id)

    summary = ctx.summarize()
    console.print(summary)


@app.command("export")
def export_context(
    context_id: str = typer.Argument(..., help="Context ID"),
    output: str = typer.Argument(..., help="Output file path"),
) -> None:
    """Export context to JSON file."""
    manager = ContextManager()
    ctx = manager.get_context(context_id)

    data = ContextSerializer.serialize(ctx)
    Path(output).write_text(json.dumps(data, indent=2))
    console.print(f"[green]Exported to:[/green] {output}")


@app.command("import")
def import_context(
    input_file: str = typer.Argument(..., help="Input file path"),
    context_id: str = typer.Option(
        None, "--id", "-i", help="Context ID (auto-generated if not provided)"
    ),
) -> None:
    """Import context from JSON file."""
    manager = ContextManager()
    data = json.loads(Path(input_file).read_text())
    ctx = ContextSerializer.deserialize(data)

    if context_id:
        manager._contexts[context_id] = ctx
        manager._save_context(context_id)

    console.print(f"[green]Imported context:[/green] {context_id or 'auto'}")
    console.print(f"  Entries: {len(ctx.entries)}")
    console.print(f"  Tokens: {ctx.used_tokens}")


@app.command("merge")
def merge_contexts(
    target: str = typer.Argument(..., help="Target context ID"),
    sources: list[str] = typer.Argument(..., help="Source context IDs"),
) -> None:
    """Merge multiple contexts into target."""
    manager = ContextManager()
    merged = manager.merge_contexts(target, sources)
    console.print(f"[green]Merged:[/green] {merged} entries into {target}")


@app.command("stats")
def context_stats(
    context_id: str = typer.Argument(..., help="Context ID"),
) -> None:
    """Show context statistics."""
    manager = ContextManager()
    stats = manager.get_stats(context_id)

    console.print(f"[bold]Context Stats:[/bold] {context_id}")
    for key, value in stats.items():
        console.print(f"  {key}: {value}")


@app.command("clear")
def clear_context(
    context_id: str = typer.Argument(..., help="Context ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clear a context."""
    if not force:
        confirm = typer.confirm(f"Clear context {context_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    manager = ContextManager()
    if manager.clear_context(context_id):
        console.print(f"[green]Cleared context:[/green] {context_id}")
    else:
        console.print(f"[red]Context not found:[/red] {context_id}")


if __name__ == "__main__":
    app()
