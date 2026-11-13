"""File editing and search CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from zksato_cli.editing.patch_engine import (
    DiffEngine,
)
from zksato_cli.editing.search import (
    DiagnosticCollector,
    RipgrepSearcher,
    SymbolSearcher,
)

app = typer.Typer(name="edit", help="File editing and search commands")
console = Console()


# Patch/Diff commands
@app.command("diff")
def diff_files(
    old_file: str = typer.Argument(..., help="Old file path"),
    new_file: str = typer.Argument(..., help="New file path"),
    context: int = typer.Option(3, "--context", "-c", help="Context lines"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Generate unified diff between two files."""
    engine = DiffEngine()
    diff = engine.generate_diff_from_files(
        Path(old_file),
        Path(new_file),
        context_lines=context,
    )
    console.print(Syntax(diff, "diff", theme="monokai", line_numbers=True))


@app.command("apply")
def apply_patch(
    patch_file: str = typer.Argument(..., help="Patch file (unified diff format)"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    backup_dir: str | None = typer.Option(None, "--backup-dir", help="Custom backup directory"),
) -> None:
    """Apply a unified diff patch."""
    # For now, read the patch file and try to apply
    # This is a simplified version - full implementation would parse the diff
    console.print("[yellow]Patch application from file not fully implemented yet[/yellow]")
    console.print("Use the PatchBuilder API for programmatic patch creation.")


@app.command("create")
def create_patch(
    label: str = typer.Option("", "--label", "-l", help="Patch label"),
    description: str = typer.Option("", "--description", "-d", help="Patch description"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Create a patch interactively (placeholder for interactive mode)."""
    console.print("[yellow]Interactive patch creation not implemented yet[/yellow]")
    console.print("Use the PatchBuilder API for programmatic patch creation.")


@app.command("preview")
def preview_patch(
    patch_file: str = typer.Argument(..., help="Patch file to preview"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Preview what a patch would do without applying."""
    console.print("[yellow]Patch preview not fully implemented yet[/yellow]")


# Search/Grep commands
@app.command("grep")
def grep_search(
    pattern: str = typer.Argument(..., help="Search pattern"),
    file_pattern: str | None = typer.Option(
        None, "--glob", "-g", help="File glob pattern (e.g., '*.py')"
    ),
    case_sensitive: bool = typer.Option(
        False, "--case-sensitive", "-s", help="Case sensitive search"
    ),
    whole_word: bool = typer.Option(False, "--word", "-w", help="Match whole words only"),
    fixed_strings: bool = typer.Option(
        False, "--fixed", "-F", help="Treat pattern as literal string"
    ),
    context: int = typer.Option(2, "--context", "-C", help="Context lines"),
    max_results: int = typer.Option(100, "--max", "-m", help="Maximum results"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Search code using ripgrep."""
    try:
        searcher = RipgrepSearcher(Path(project_root))
        results = searcher.search(
            pattern,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive,
            whole_word=whole_word,
            regex=not fixed_strings,
            max_results=max_results,
            context_lines=context,
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return

    if not results.results:
        console.print(f"[yellow]No matches found for:[/yellow] {pattern}")
        return

    console.print(
        f"[green]Found {results.total_matches} matches in {results.files_with_matches} files ({results.elapsed_ms:.1f}ms):[/green]\n"
    )

    current_file = None
    for result in results.results:
        if result.file_path != current_file:
            current_file = result.file_path
            console.print(f"[bold cyan]{current_file}[/bold cyan]")

        # Highlight match
        line = result.line
        if result.match_start >= 0 and result.match_end >= 0:
            before = line[: result.match_start]
            match = line[result.match_start : result.match_end]
            after = line[result.match_end :]
            highlighted = f"{before}[bold yellow]{match}[/bold yellow]{after}"
        else:
            highlighted = line

        console.print(f"  {result.line_number:4}: {highlighted}")

        for ctx in result.context_before:
            console.print(f"  {'':4} [dim]{ctx.rstrip()}[/dim]")
        for ctx in result.context_after:
            console.print(f"  {'':4} [dim]{ctx.rstrip()}[/dim]")

    if results.truncated:
        console.print(f"\n[yellow]Results truncated at {max_results} matches[/yellow]")


@app.command("symbol")
def symbol_search(
    symbol: str = typer.Argument(..., help="Symbol name to search for"),
    language: str | None = typer.Option(
        None, "--lang", "-l", help="Language (python, rust, javascript, etc.)"
    ),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Search for symbol definitions."""
    searcher = SymbolSearcher(Path(project_root))
    results = searcher.find_definition(symbol, language)

    if not results.results:
        console.print(f"[yellow]No definitions found for:[/yellow] {symbol}")
        return

    console.print(f"[green]Found {len(results.results)} definition(s) for:[/green] {symbol}\n")

    for result in results.results:
        console.print(f"[bold cyan]{result.file_path}:{result.line_number}[/bold cyan]")
        console.print(f"  {result.line.strip()}\n")


@app.command("references")
def symbol_references(
    symbol: str = typer.Argument(..., help="Symbol name to find references for"),
    language: str | None = typer.Option(None, "--lang", "-l", help="Language"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Find symbol references."""
    searcher = SymbolSearcher(Path(project_root))
    results = searcher.find_references(symbol, language)

    if not results.results:
        console.print(f"[yellow]No references found for:[/yellow] {symbol}")
        return

    console.print(f"[green]Found {len(results.results)} reference(s) for:[/green] {symbol}\n")

    current_file = None
    for result in results.results:
        if result.file_path != current_file:
            current_file = result.file_path
            console.print(f"[bold cyan]{current_file}[/bold cyan]")
        console.print(f"  {result.line_number:4}: {result.line.strip()}")


@app.command("diagnostics")
def run_diagnostics(
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
) -> None:
    """Run code diagnostics (lint, type-check)."""
    collector = DiagnosticCollector(Path(project_root))
    diagnostics = collector.collect_all()

    if not diagnostics:
        console.print("[green]No diagnostics found[/green]")
        return

    if format == "json":
        import json

        console.print(json.dumps(diagnostics, indent=2))
        return

    table = Table(title="Diagnostics")
    table.add_column("File")
    table.add_column("Line")
    table.add_column("Col")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Message")
    table.add_column("Source")

    for diag in diagnostics:
        severity_color = "red" if diag.get("severity") == "error" else "yellow"
        table.add_row(
            diag.get("file", ""),
            str(diag.get("line", 0)),
            str(diag.get("column", 0)),
            f"[{severity_color}]{diag.get('severity', '')}[/]",
            diag.get("code", ""),
            diag.get("message", "")[:80],
            diag.get("source", ""),
        )

    console.print(table)
    console.print(f"\n[bold]Total: {len(diagnostics)} diagnostic(s)[/bold]")


# File operations
@app.command("read")
def read_file(
    file_path: str = typer.Argument(..., help="File to read"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    start: int | None = typer.Option(None, "--start", "-s", help="Start line"),
    end: int | None = typer.Option(None, "--end", "-e", help="End line"),
) -> None:
    """Read a file with syntax highlighting."""
    path = Path(project_root) / file_path
    if not path.exists():
        console.print(f"[red]File not found:[/red] {file_path}")
        return

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if start is not None or end is not None:
        s = (start or 1) - 1
        e = end if end is not None else len(lines)
        lines = lines[s:e]
        content = "\n".join(lines)

    # Determine syntax from extension
    suffix = path.suffix.lower()
    syntax_map = {
        ".py": "python",
        ".rs": "rust",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".java": "java",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".sh": "bash",
        ".sql": "sql",
    }
    syntax = syntax_map.get(suffix, "text")

    console.print(Syntax(content, syntax, theme="monokai", line_numbers=True))


@app.command("write")
def write_file(
    file_path: str = typer.Argument(..., help="File to write"),
    content: str = typer.Argument(..., help="Content to write"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite without confirmation"),
) -> None:
    """Write content to a file."""
    path = Path(project_root) / file_path

    if path.exists() and not force:
        confirm = typer.confirm(f"File exists. Overwrite {file_path}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    console.print(f"[green]Written:[/green] {file_path} ({len(content)} bytes)")


@app.command("edit")
def edit_file(
    file_path: str = typer.Argument(..., help="File to edit"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
) -> None:
    """Open file in editor (placeholder)."""
    console.print("[yellow]Interactive editing not implemented yet[/yellow]")
    console.print("Use 'zksato edit read' and 'zksato edit write' for now.")


if __name__ == "__main__":
    app()
