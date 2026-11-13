"""Git integration commands for ZKSATO."""

import subprocess

import typer
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer(name="git", help="Git integration commands")
console = Console()


@app.command("status")
def git_status(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
) -> None:
    """Show git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            console.print("[bold]Changes:[/bold]")
            for line in result.stdout.strip().split("\n"):
                if line:
                    status = line[:2]
                    file = line[3:]
                    color = "green" if "?" in status else "yellow" if "M" in status else "red"
                    console.print(f"  [{color}]{status}[/] {file}")
        else:
            console.print("[green]Working tree clean[/green]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("diff")
def git_diff(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    staged: bool = typer.Option(False, "--staged", "-s", help="Show staged changes"),
    file: str | None = typer.Option(None, "--file", "-f", help="Specific file"),
) -> None:
    """Show git diff."""
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if file:
            cmd.append(file)

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            console.print(Syntax(result.stdout, "diff", theme="monokai", line_numbers=True))
        else:
            console.print("[yellow]No changes[/yellow]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("log")
def git_log(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of commits"),
    oneline: bool = typer.Option(True, "--oneline/--no-oneline", help="One line per commit"),
) -> None:
    """Show git log."""
    try:
        cmd = ["git", "log", f"-{limit}"]
        if oneline:
            cmd.append("--oneline")

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            console.print(result.stdout)
        else:
            console.print("[yellow]No commits[/yellow]")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("branch")
def git_branch(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    all_branches: bool = typer.Option(False, "--all", "-a", help="Show all branches"),
    create: str | None = typer.Option(None, "--create", "-c", help="Create new branch"),
    delete: str | None = typer.Option(None, "--delete", "-d", help="Delete branch"),
    switch: str | None = typer.Option(None, "--switch", "-s", help="Switch to branch"),
) -> None:
    """Manage git branches."""
    try:
        if create:
            result = subprocess.run(
                ["git", "branch", create],
                cwd=path,
                capture_output=True,
                text=True,
            )
            console.print(f"[green]Created branch:[/green] {create}")
            return

        if delete:
            result = subprocess.run(
                ["git", "branch", "-d", delete],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Deleted branch:[/green] {delete}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        if switch:
            result = subprocess.run(
                ["git", "switch", switch],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Switched to:[/green] {switch}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        # List branches
        cmd = ["git", "branch"]
        if all_branches:
            cmd.append("-a")

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line.startswith("*"):
                    console.print(f"[green]{line}[/green]")
                else:
                    console.print(f"  {line}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("commit")
def git_commit(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
    add_all: bool = typer.Option(False, "--all", "-a", help="Stage all changes"),
    signoff: bool = typer.Option(False, "--signoff", "-s", help="Add signoff"),
    amend: bool = typer.Option(False, "--amend", help="Amend last commit"),
) -> None:
    """Create a git commit."""
    try:
        if add_all:
            subprocess.run(["git", "add", "-A"], cwd=path, check=True)

        cmd = ["git", "commit"]
        if signoff:
            cmd.append("-s")
        if amend:
            cmd.append("--amend")
        cmd.extend(["-m", message])

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Commit created[/green]")
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] {result.stderr}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("push")
def git_push(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    remote: str = typer.Option("origin", "--remote", "-r", help="Remote name"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force push"),
) -> None:
    """Push to remote."""
    try:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        if force:
            cmd.append("--force")

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Push successful[/green]")
        else:
            console.print(f"[red]Error:[/red] {result.stderr}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("pull")
def git_pull(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    remote: str = typer.Option("origin", "--remote", "-r", help="Remote name"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch name"),
) -> None:
    """Pull from remote."""
    try:
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Pull successful[/green]")
            console.print(result.stdout)
        else:
            console.print(f"[red]Error:[/red] {result.stderr}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("worktree")
def git_worktree(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    list_worktrees: bool = typer.Option(False, "--list", "-l", help="List worktrees"),
    add: str | None = typer.Option(None, "--add", "-a", help="Add worktree (path)"),
    branch: str | None = typer.Option(None, "--branch", "-b", help="Branch for new worktree"),
    remove: str | None = typer.Option(None, "--remove", "-r", help="Remove worktree"),
) -> None:
    """Manage git worktrees."""
    try:
        if list_worktrees:
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    console.print(line)
            return

        if add:
            if not branch:
                console.print("[red]Error:[/red] --branch required for --add")
                return
            result = subprocess.run(
                ["git", "worktree", "add", add, branch],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Worktree added:[/green] {add} -> {branch}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        if remove:
            result = subprocess.run(
                ["git", "worktree", "remove", remove],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Worktree removed:[/green] {remove}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("stash")
def git_stash(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    list_stashes: bool = typer.Option(False, "--list", "-l", help="List stashes"),
    push: str | None = typer.Option(None, "--push", "-p", help="Stash message"),
    pop: bool = typer.Option(False, "--pop", help="Pop latest stash"),
    drop: str | None = typer.Option(None, "--drop", "-d", help="Drop stash by index"),
) -> None:
    """Manage git stashes."""
    try:
        if list_stashes:
            result = subprocess.run(
                ["git", "stash", "list"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    console.print(line)
            return

        if push is not None:
            result = subprocess.run(
                ["git", "stash", "push", "-m", push],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Stashed:[/green] {push}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        if pop:
            result = subprocess.run(
                ["git", "stash", "pop"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print("[green]Stash popped[/green]")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        if drop is not None:
            result = subprocess.run(
                ["git", "stash", "drop", f"stash@{{{drop}}}"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Stash dropped:[/green] {drop}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


@app.command("remote")
def git_remote(
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    list_remotes: bool = typer.Option(False, "--list", "-l", help="List remotes"),
    add: str | None = typer.Option(None, "--add", "-a", help="Add remote (name url)"),
    remove: str | None = typer.Option(None, "--remove", "-r", help="Remove remote"),
) -> None:
    """Manage git remotes."""
    try:
        if list_remotes:
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                console.print(result.stdout)
            return

        if add:
            parts = add.split()
            if len(parts) != 2:
                console.print("[red]Error:[/red] Usage: --add 'name url'")
                return
            result = subprocess.run(
                ["git", "remote", "add", parts[0], parts[1]],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Remote added:[/green] {parts[0]} -> {parts[1]}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
            return

        if remove:
            result = subprocess.run(
                ["git", "remote", "remove", remove],
                cwd=path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                console.print(f"[green]Remote removed:[/green] {remove}")
            else:
                console.print(f"[red]Error:[/red] {result.stderr}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")


if __name__ == "__main__":
    app()
