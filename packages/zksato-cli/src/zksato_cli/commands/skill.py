"""Skill CLI commands."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zksato_cli.hooks.framework import HookManager, setup_builtin_hooks
from zksato_cli.skills.system import (
    SkillManager,
    SkillManifest,
    SkillScope,
    SkillValidator,
    register_builtin_skills,
)

app = typer.Typer(name="skill", help="Skill management commands")
console = Console()


@app.command("list")
def list_skills(
    scope: str | None = typer.Option(
        None, "--scope", "-s", help="Filter by scope (user, project, builtin)"
    ),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """List available skills."""
    hook_manager = HookManager()
    from zksato_cli.hooks.framework import setup_builtin_hooks

    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    scope_filter = SkillScope(scope) if scope else None
    skills = skill_manager.list_skills(scope_filter)

    if not skills:
        console.print("[yellow]No skills found[/yellow]")
        return

    table = Table(title="Available Skills")
    table.add_column("Skill ID")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Scope")
    table.add_column("Description")
    table.add_column("Provides")

    for skill in skills:
        table.add_row(
            skill.skill_id[:30],
            skill.name,
            skill.version,
            skill.scope.value,
            skill.description[:50],
            ", ".join(skill.provides[:3]),
        )

    console.print(table)


@app.command("show")
def show_skill(
    skill_id: str = typer.Argument(..., help="Skill ID"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """Show skill details."""
    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    skill = skill_manager.get_skill(skill_id)

    if not skill:
        console.print(f"[red]Skill not found: {skill_id}[/red]")
        return

    console.print(f"[bold]Skill:[/bold] {skill.name}")
    console.print(f"  ID: {skill.skill_id}")
    console.print(f"  Version: {skill.version}")
    console.print(f"  Scope: {skill.scope.value}")
    console.print(f"  Description: {skill.description}")
    console.print(f"  Author: {skill.author}")
    console.print(f"  Provides: {', '.join(skill.provides)}")
    console.print(f"  Requires: {', '.join(skill.requires)}")
    console.print(f"  Entry point: {skill.entry_point}")
    console.print(f"  Tags: {', '.join(skill.tags)}")

    if skill.parameters:
        console.print("\n[bold]Parameters:[/bold]")
        for param in skill.parameters:
            required = " (required)" if param.required else " (optional)"
            default = f" = {param.default}" if param.default is not None else ""
            console.print(f"  {param.name}: {param.type}{required}{default} - {param.description}")

    if skill.dependencies:
        console.print("\n[bold]Dependencies:[/bold]")
        for dep in skill.dependencies:
            version = f" @ {dep.version}" if dep.version else ""
            required = " (required)" if dep.required else " (optional)"
            console.print(f"  {dep.skill_id}{version}{required}")


@app.command("install")
def install_skill(
    file_path: str = typer.Argument(..., help="Path to skill manifest file (JSON or YAML)"),
    scope: str = typer.Option("project", "--scope", "-s", help="Install scope (user, project)"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """Install a skill from a manifest file."""
    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    scope_enum = SkillScope(scope)
    if skill_manager.install_skill(Path(file_path), scope_enum):
        console.print(f"[green]Installed skill from:[/green] {file_path}")
    else:
        console.print("[red]Failed to install skill[/red]")


@app.command("uninstall")
def uninstall_skill(
    skill_id: str = typer.Argument(..., help="Skill ID"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Uninstall a skill."""
    if not force:
        confirm = typer.confirm(f"Uninstall skill {skill_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    if skill_manager.uninstall_skill(skill_id):
        console.print(f"[green]Uninstalled skill:[/green] {skill_id}")
    else:
        console.print(f"[red]Skill not found:[/red] {skill_id}")


@app.command("create-instance")
def create_instance(
    skill_id: str = typer.Argument(..., help="Skill ID"),
    config: str = typer.Option("{}", "--config", "-c", help="Configuration (JSON)"),
    scope: str = typer.Option("project", "--scope", "-s", help="Instance scope"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """Create a skill instance."""
    import json

    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    SkillScope(scope)
    instance_config = json.loads(config)

    instance = skill_manager.create_instance(skill_id, instance_config, SkillScope(scope))

    if instance:
        console.print(f"[green]Created instance:[/green] {instance.instance_id}")
        console.print(f"  Skill: {skill_id}")
        console.print(f"  Config: {instance.config}")
    else:
        console.print("[red]Failed to create instance[/red]")


@app.command("execute")
def execute_skill(
    instance_id: str = typer.Argument(..., help="Instance ID"),
    params: str = typer.Option("{}", "--params", "-P", help="Execution parameters (JSON)"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """Execute a skill instance."""
    import json

    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    execution_params = json.loads(params)

    async def run():
        return await skill_manager.execute(instance_id, execution_params, session_id)

    result = asyncio.run(run())

    if result.success:
        console.print(f"[green]Skill executed successfully:[/green] {instance_id}")
        console.print(f"  Duration: {result.duration_ms:.1f}ms")
        if result.output:
            console.print(f"  Output: {result.output}")
    else:
        console.print(f"[red]Skill execution failed:[/red] {instance_id}")
        console.print(f"  Error: {result.error}")


@app.command("validate")
def validate_skill(
    file_path: str = typer.Argument(..., help="Path to skill manifest file"),
) -> None:
    """Validate a skill manifest file."""
    import yaml

    try:
        with Path(file_path).open("r") as f:
            data = json.load(f) if file_path.endswith(".json") else yaml.safe_load(f)

        manifest = SkillManifest.from_dict(data)
        errors = SkillValidator.validate_manifest(manifest)

        if errors:
            console.print("[red]Validation failed:[/red]")
            for error in errors:
                console.print(f"  - {error}")
        else:
            console.print(f"[green]Manifest is valid:[/green] {manifest.name} v{manifest.version}")

    except Exception as exc:
        console.print(f"[red]Validation error:[/red] {exc}")


@app.command("validate-config")
def validate_config(
    skill_id: str = typer.Argument(..., help="Skill ID"),
    config: str = typer.Argument(..., help="Configuration (JSON)"),
    project_root: str = typer.Option(".", "--project", "-p", help="Project root directory"),
    storage_dir: str = typer.Option(".zksato/skills", "--storage", help="Skill storage directory"),
) -> None:
    """Validate a skill configuration."""
    import json

    hook_manager = HookManager()
    setup_builtin_hooks(hook_manager)

    skill_manager = SkillManager(Path(project_root), storage_dir, hook_manager)
    register_builtin_skills(skill_manager.registry)

    instance_config = json.loads(config)
    errors = skill_manager.validate_config(skill_id, instance_config)

    if errors:
        console.print("[red]Configuration invalid:[/red]")
        for error in errors:
            console.print(f"  - {error}")
    else:
        console.print("[green]Configuration is valid[/green]")


if __name__ == "__main__":
    app()
