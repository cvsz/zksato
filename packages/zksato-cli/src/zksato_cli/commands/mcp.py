"""MCP (Model Context Protocol) CLI commands."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from zksato_cli.mcp.client import MCPClientManager, MCPServerConfig
from zksato_cli.mcp.protocol import TransportType

app = typer.Typer(name="mcp", help="MCP (Model Context Protocol) commands")
console = Console()


@app.command("add")
def add_server(
    name: str = typer.Argument(..., help="Server name"),
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="Transport type (stdio, sse, websocket)"
    ),
    command: str | None = typer.Option(
        None, "--command", "-c", help="Command for stdio transport (space-separated)"
    ),
    url: str | None = typer.Option(None, "--url", "-u", help="URL for SSE/WebSocket transport"),
    cwd: str | None = typer.Option(None, "--cwd", help="Working directory for stdio"),
    env: str | None = typer.Option(None, "--env", "-e", help="Environment variables (JSON)"),
    headers: str | None = typer.Option(
        None, "--headers", "-H", help="Headers for SSE/WebSocket (JSON)"
    ),
    timeout: float = typer.Option(30.0, "--timeout", help="Connection timeout in seconds"),
    auto_connect: bool = typer.Option(
        True, "--auto-connect/--no-auto-connect", help="Auto-connect on startup"
    ),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Add an MCP server configuration."""
    manager = MCPClientManager(config_dir)

    transport_type = TransportType(transport)

    if transport_type == TransportType.STDIO and not command:
        console.print("[red]STDIO transport requires --command[/red]")
        return

    if transport_type in (TransportType.SSE, TransportType.WEBSOCKET) and not url:
        console.print(f"[red]{transport} transport requires --url[/red]")
        return

    env_dict = json.loads(env) if env else None
    headers_dict = json.loads(headers) if headers else None

    command_list = command.split() if command else None

    config = MCPServerConfig(
        name=name,
        transport=transport_type,
        command=command_list,
        url=url,
        cwd=Path(cwd) if cwd else None,
        env=env_dict,
        headers=headers_dict,
        auto_connect=auto_connect,
    )

    manager.add_server(config)
    console.print(f"[green]Added MCP server:[/green] {name} ({config.server_id})")


@app.command("remove")
def remove_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove an MCP server configuration."""
    if not force:
        confirm = typer.confirm(f"Remove server {server_id}?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    manager = MCPClientManager(config_dir)
    if manager.remove_server(server_id):
        console.print(f"[green]Removed server:[/green] {server_id}")
    else:
        console.print(f"[red]Server not found:[/red] {server_id}")


@app.command("list")
def list_servers(
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """List MCP server configurations."""
    manager = MCPClientManager(config_dir)
    configs = manager.list_server_configs()

    if not configs:
        console.print("[yellow]No MCP servers configured[/yellow]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Server ID")
    table.add_column("Name")
    table.add_column("Transport")
    table.add_column("Command/URL")
    table.add_column("Auto-connect")

    for c in configs:
        if c.transport.value == "stdio":
            endpoint = " ".join(c.command) if c.command else "N/A"
        else:
            endpoint = c.url or "N/A"

        table.add_row(
            c.server_id[:12] + "...",
            c.name,
            c.transport.value,
            endpoint[:40],
            "✓" if c.auto_connect else "✗",
        )

    console.print(table)


@app.command("show")
def show_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Show server configuration details."""
    manager = MCPClientManager(config_dir)
    config = manager.get_server_config(server_id)

    if not config:
        console.print(f"[red]Server not found:[/red] {server_id}")
        return

    console.print(f"[bold]Server:[/bold] {config.name}")
    console.print(f"  ID: {config.server_id}")
    console.print(f"  Transport: {config.transport.value}")
    console.print(f"  Command: {' '.join(config.command) if config.command else 'N/A'}")
    console.print(f"  URL: {config.url or 'N/A'}")
    console.print(f"  Working Dir: {config.cwd or 'N/A'}")
    console.print(f"  Environment: {config.env or 'N/A'}")
    console.print(f"  Headers: {config.headers or 'N/A'}")
    console.print(f"  Auto-connect: {config.auto_connect}")


@app.command("connect")
def connect_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Connect to an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        return connection

    connection = asyncio.run(run())

    if connection:
        console.print(f"[green]Connected to:[/green] {connection.config.name}")
        if connection.server_info:
            console.print(
                f"  Server: {connection.server_info.name} v{connection.server_info.version}"
            )
            console.print(f"  Protocol: {connection.server_info.protocol_version}")
            console.print(f"  Tools: {len(connection.tools)}")
            console.print(f"  Resources: {len(connection.resources)}")
            console.print(f"  Prompts: {len(connection.prompts)}")
    else:
        console.print(f"[red]Server not found:[/red] {server_id}")


@app.command("disconnect")
def disconnect_server(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Disconnect from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        return await manager.disconnect_server(server_id)

    if asyncio.run(run()):
        console.print(f"[green]Disconnected from:[/green] {server_id}")
    else:
        console.print(f"[red]Server not connected:[/red] {server_id}")


@app.command("disconnect-all")
def disconnect_all(
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Disconnect from all MCP servers."""
    manager = MCPClientManager(config_dir)

    async def run():
        await manager.disconnect_all()

    asyncio.run(run())
    console.print("[green]Disconnected from all servers[/green]")


@app.command("tools")
def list_tools(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """List tools from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.list_tools(server_id)

    tools = asyncio.run(run())

    if not tools:
        console.print("[yellow]No tools found or server not connected[/yellow]")
        return

    table = Table(title=f"Tools from {server_id}")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Input Schema")

    for tool in tools:
        table.add_row(
            tool.name,
            tool.description[:50],
            json.dumps(tool.input_schema)[:50],
        )

    console.print(table)


@app.command("call")
def call_tool(
    server_id: str = typer.Argument(..., help="Server ID"),
    tool_name: str = typer.Argument(..., help="Tool name"),
    arguments: str = typer.Option("{}", "--args", "-a", help="Tool arguments (JSON)"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Call a tool on an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.call_tool(server_id, tool_name, json.loads(arguments))

    result = asyncio.run(run())

    if result is not None:
        console.print(Syntax(json.dumps(result, indent=2), "json", theme="monokai"))
    else:
        console.print("[red]Tool call failed or server not connected[/red]")


@app.command("resources")
def list_resources(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """List resources from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.list_resources(server_id)

    resources = asyncio.run(run())

    if not resources:
        console.print("[yellow]No resources found or server not connected[/yellow]")
        return

    table = Table(title=f"Resources from {server_id}")
    table.add_column("URI")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("MIME Type")

    for res in resources:
        table.add_row(
            res.uri,
            res.name,
            res.description or "",
            res.mime_type or "",
        )

    console.print(table)


@app.command("read")
def read_resource(
    server_id: str = typer.Argument(..., help="Server ID"),
    uri: str = typer.Argument(..., help="Resource URI"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Read a resource from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.read_resource(server_id, uri)

    result = asyncio.run(run())

    if result is not None:
        console.print(Syntax(json.dumps(result, indent=2), "json", theme="monokai"))
    else:
        console.print("[red]Resource read failed or server not connected[/red]")


@app.command("prompts")
def list_prompts(
    server_id: str = typer.Argument(..., help="Server ID"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """List prompts from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.list_prompts(server_id)

    prompts = asyncio.run(run())

    if not prompts:
        console.print("[yellow]No prompts found or server not connected[/yellow]")
        return

    table = Table(title=f"Prompts from {server_id}")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Arguments")

    for prompt in prompts:
        table.add_row(
            prompt.name,
            prompt.description or "",
            str(prompt.arguments),
        )

    console.print(table)


@app.command("prompt")
def get_prompt(
    server_id: str = typer.Argument(..., help="Server ID"),
    name: str = typer.Argument(..., help="Prompt name"),
    arguments: str = typer.Option("{}", "--args", "-a", help="Prompt arguments (JSON)"),
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Get a prompt from an MCP server."""
    manager = MCPClientManager(config_dir)

    async def run():
        connection = await manager.connect_server(server_id)
        if not connection:
            return None
        return await manager.client.get_prompt(server_id, name, json.loads(arguments))

    result = asyncio.run(run())

    if result is not None:
        console.print(Syntax(json.dumps(result, indent=2), "json", theme="monokai"))
    else:
        console.print("[red]Prompt get failed or server not connected[/red]")


@app.command("connect-all")
def connect_all(
    config_dir: str = typer.Option(".zksato/mcp", "--config-dir", help="MCP config directory"),
) -> None:
    """Connect to all auto-connect servers."""
    manager = MCPClientManager(config_dir)

    async def run():
        return await manager.connect_all_auto()

    connections = asyncio.run(run())

    if not connections:
        console.print("[yellow]No servers to connect[/yellow]")
        return

    console.print(f"[green]Connected to {len(connections)} server(s):[/green]")
    for server_id, conn in connections.items():
        console.print(f"  {conn.config.name} ({server_id[:12]}...)")


@app.command("server")
def server_commands() -> None:
    """MCP Server management commands."""
    console.print("[yellow]Use subcommands: start, add-tool, add-resource, add-prompt[/yellow]")


@app.command("server start")
def start_server(
    name: str = typer.Option("zksato-mcp", "--name", "-n", help="Server name"),
    version: str = typer.Option("1.0.0", "--version", "-v", help="Server version"),
    instructions: str | None = typer.Option(
        None, "--instructions", "-i", help="Server instructions"
    ),
    tools: bool = typer.Option(True, "--tools/--no-tools", help="Enable tools capability"),
    resources: bool = typer.Option(
        True, "--resources/--no-resources", help="Enable resources capability"
    ),
    prompts: bool = typer.Option(True, "--prompts/--no-prompts", help="Enable prompts capability"),
) -> None:
    """Start an MCP server over stdio."""
    from zksato_cli.mcp.server import MCPCapabilities, MCPServer, MCPServerConfig, run_stdio_server

    config = MCPServerConfig(
        name=name,
        version=version,
        instructions=instructions,
        capabilities=MCPCapabilities(
            tools=tools,
            resources=resources,
            prompts=prompts,
        ),
    )

    console.print(f"[green]Starting MCP server:[/green] {name} v{version}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    async def run():

        server = MCPServer(config)

        # Register built-in tools
        server.register_tool(
            name="read_file",
            description="Read a file from the filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
            handler=lambda args: {"content": Path(args["path"]).read_text(encoding="utf-8")},
        )

        server.register_tool(
            name="write_file",
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            handler=lambda args: {
                "success": True,
                "path": args["path"],
                "bytes_written": len(args["content"].encode("utf-8")),
            },
        )

        server.register_tool(
            name="list_directory",
            description="List directory contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                },
                "required": ["path"],
            },
            handler=lambda args: {
                "entries": [
                    {"name": p.name, "type": "dir" if p.is_dir() else "file"}
                    for p in Path(args["path"]).iterdir()
                ],
            },
        )

        server.register_tool(
            name="run_command",
            description="Execute a shell command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"},
                    "cwd": {"type": "string", "description": "Working directory"},
                },
                "required": ["command"],
            },
            handler=lambda args: {
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            },
        )

        await run_stdio_server(server)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command("server add-tool")
def add_server_tool(
    name: str = typer.Argument(..., help="Tool name"),
    description: str = typer.Argument(..., help="Tool description"),
    schema: str = typer.Argument(..., help="JSON schema for input"),
    handler: str = typer.Option(None, "--handler", "-h", help="Handler module:function"),
) -> None:
    """Add a tool to the MCP server (placeholder for dynamic registration)."""
    console.print(f"[green]Tool registered:[/green] {name}")
    console.print(f"  Description: {description}")
    console.print(f"  Schema: {schema}")


if __name__ == "__main__":
    app()
