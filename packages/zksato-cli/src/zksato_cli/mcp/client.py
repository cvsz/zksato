"""MCP Client for connecting to and interacting with MCP servers."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zksato_cli.mcp.protocol import (
    MCPCapabilities,
    MCPClientInfo,
    MCPMethod,
    MCPNotification,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    MCPTransport,
    SSETransport,
    StdioTransport,
    TransportType,
    WebSocketTransport,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    server_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    transport: TransportType = TransportType.STDIO

    # Stdio transport
    command: list[str] | None = None
    cwd: Path | None = None
    env: dict[str, str] | None = None

    # SSE/WebSocket transport
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    # Connection settings
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0

    # Capabilities
    required_capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)

    # Auto-connect
    auto_connect: bool = True


@dataclass
class MCPConnection:
    """Active MCP server connection."""

    config: MCPServerConfig
    transport: MCPTransport
    server_info: MCPServerInfo | None = None
    connected_at: datetime | None = None
    last_ping: datetime | None = None
    is_healthy: bool = True
    error_count: int = 0
    tools: list[MCPTool] = field(default_factory=list)
    resources: list[MCPResource] = field(default_factory=list)
    prompts: list[MCPPrompt] = field(default_factory=list)


class MCPClient:
    """MCP client for managing multiple server connections."""

    def __init__(
        self,
        client_info: MCPClientInfo | None = None,
        default_timeout: float = 30.0,
    ) -> None:
        self.client_info = client_info or MCPClientInfo(
            name="zksato",
            version="1.0.0",
        )
        self.default_timeout = default_timeout
        self._connections: dict[str, MCPConnection] = {}
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._notification_handlers: dict[str, list[Callable]] = {}
        self._running = False
        self._receive_tasks: dict[str, asyncio.Task] = {}

    def _create_transport(self, config: MCPServerConfig) -> MCPTransport:
        """Create transport based on configuration."""
        if config.transport == TransportType.STDIO:
            if not config.command:
                raise ValueError("STDIO transport requires command")
            return StdioTransport(
                command=config.command,
                cwd=config.cwd,
                env=config.env,
            )
        elif config.transport == TransportType.SSE:
            if not config.url:
                raise ValueError("SSE transport requires URL")
            return SSETransport(url=config.url, headers=config.headers)
        elif config.transport == TransportType.WEBSOCKET:
            if not config.url:
                raise ValueError("WebSocket transport requires URL")
            return WebSocketTransport(url=config.url, headers=config.headers)
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

    async def connect_server(self, config: MCPServerConfig) -> MCPConnection:
        """Connect to an MCP server."""
        if config.server_id in self._connections:
            existing = self._connections[config.server_id]
            if await existing.transport.is_connected():
                logger.info("Already connected to server: %s", config.server_id)
                return existing

        transport = self._create_transport(config)

        # Connect with retries
        for attempt in range(config.retry_attempts + 1):
            try:
                await transport.connect()
                break
            except Exception as exc:
                if attempt < config.retry_attempts:
                    logger.warning(
                        "Connection attempt %d failed for %s: %s",
                        attempt + 1,
                        config.server_id,
                        exc,
                    )
                    await asyncio.sleep(config.retry_delay_seconds * (attempt + 1))
                else:
                    raise

        connection = MCPConnection(
            config=config,
            transport=transport,
            connected_at=datetime.now(UTC),
        )

        # Initialize the connection
        await self._initialize_connection(connection)

        # Start receiving messages
        self._receive_tasks[config.server_id] = asyncio.create_task(
            self._receive_loop(config.server_id)
        )

        self._connections[config.server_id] = connection
        logger.info("Connected to MCP server: %s", config.server_id)
        return connection

    async def _initialize_connection(self, connection: MCPConnection) -> None:
        """Perform MCP initialize handshake."""
        request = MCPRequest(
            method=MCPMethod.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": self.client_info.capabilities.to_dict(),
                "clientInfo": {
                    "name": self.client_info.name,
                    "version": self.client_info.version,
                },
            },
        )

        response = await self._send_request(connection, request, timeout=30.0)

        if response.error:
            raise RuntimeError(f"Initialize failed: {response.error}")

        server_info = MCPServerInfo(
            name=response.result.get("serverInfo", {}).get("name", "unknown"),
            version=response.result.get("serverInfo", {}).get("version", "unknown"),
            protocol_version=response.result.get("protocolVersion", "2024-11-05"),
            capabilities=MCPCapabilities.from_dict(response.result.get("capabilities", {})),
            instructions=response.result.get("instructions"),
        )

        connection.server_info = server_info

        # Send initialized notification
        initialized = MCPNotification(
            method=MCPMethod.INITIALIZED,
        )
        await connection.transport.send(initialized.to_dict())

        # Discover capabilities
        await self._discover_capabilities(connection)

    async def _discover_capabilities(self, connection: MCPConnection) -> None:
        """Discover tools, resources, and prompts."""
        server_info = connection.config.server_info

        # List tools
        if server_info and server_info.capabilities.tools:
            try:
                response = await self._send_request(
                    connection,
                    MCPRequest(method=MCPMethod.TOOLS_LIST),
                )
                if response.result and "tools" in response.result:
                    connection.tools = [MCPTool(**t) for t in response.result["tools"]]
            except Exception as exc:
                logger.warning("Failed to list tools: %s", exc)

        # List resources
        if server_info and server_info.capabilities.resources:
            try:
                response = await self._send_request(
                    connection,
                    MCPRequest(method=MCPMethod.RESOURCES_LIST),
                )
                if response.result and "resources" in response.result:
                    connection.resources = [MCPResource(**r) for r in response.result["resources"]]
            except Exception as exc:
                logger.warning("Failed to list resources: %s", exc)

        # List prompts
        if server_info and server_info.capabilities.prompts:
            try:
                response = await self._send_request(
                    connection,
                    MCPRequest(method=MCPMethod.PROMPTS_LIST),
                )
                if response.result and "prompts" in response.result:
                    connection.prompts = [MCPPrompt(**p) for p in response.result["prompts"]]
            except Exception as exc:
                logger.warning("Failed to list prompts: %s", exc)

    async def _send_request(
        self,
        connection: MCPConnection,
        request: MCPRequest,
        timeout: float | None = None,
    ) -> MCPResponse:
        """Send a request and wait for response."""
        request_id = request.id or str(uuid.uuid4())
        request.id = request_id

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await connection.transport.send(request.to_dict())

            # Wait for response with timeout
            response_dict = await asyncio.wait_for(
                future,
                timeout=timeout or self.default_timeout,
            )

            return MCPResponse(
                id=response_dict.get("id"),
                result=response_dict.get("result"),
                error=response_dict.get("error"),
            )

        finally:
            self._pending_requests.pop(request_id, None)

    async def _receive_loop(self, server_id: str) -> None:
        """Background task to receive messages from server."""
        connection = self._connections.get(server_id)
        if not connection:
            return

        while True:
            try:
                message = await connection.transport.receive()
                if message is None:
                    break

                # Handle response
                if "id" in message and message["id"] in self._pending_requests:
                    future = self._pending_requests.pop(message["id"])
                    if not future.done():
                        future.set_result(message)
                    continue

                # Handle notification
                if "method" in message and "id" not in message:
                    await self._handle_notification(server_id, message)
                    continue

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in receive loop for %s: %s", server_id, exc)
                break

        # Connection lost
        if server_id in self._connections:
            self._connections[server_id].is_healthy = False

    async def _handle_notification(self, server_id: str, message: dict[str, Any]) -> None:
        """Handle incoming notification."""
        method = message.get("method", "")
        params = message.get("params", {})

        handlers = self._notification_handlers.get(method, [])
        for handler in handlers:
            try:
                await handler(server_id, params)
            except Exception as exc:
                logger.error("Notification handler error: %s", exc)

    def register_notification_handler(
        self,
        method: str,
        handler: Callable[[str, dict[str, Any]], Any],
    ) -> None:
        """Register a notification handler."""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from an MCP server."""
        connection = self._connections.get(server_id)
        if not connection:
            return False

        # Send shutdown request
        try:
            request = MCPRequest(method=MCPMethod.SHUTDOWN)
            await connection.transport.send(request.to_dict())
        except Exception:
            pass

        # Cancel receive task
        task = self._receive_tasks.pop(server_id, None)
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Disconnect transport
        await connection.transport.disconnect()

        del self._connections[server_id]
        logger.info("Disconnected from server: %s", server_id)
        return True

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for server_id in list(self._connections.keys()):
            await self.disconnect_server(server_id)

    # Tool methods
    async def list_tools(self, server_id: str) -> list[MCPTool]:
        """List tools from a server."""
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")
        return list(connection.tools)

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a tool on a server."""
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")

        request = MCPRequest(
            method=MCPMethod.TOOLS_CALL,
            params={
                "name": tool_name,
                "arguments": arguments,
            },
        )

        response = await self._send_request(connection, request)

        if response.error:
            raise RuntimeError(f"Tool call failed: {response.error}")

        return response.result

    # Resource methods
    async def list_resources(self, server_id: str) -> list[MCPResource]:
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")
        return list(connection.resources)

    async def read_resource(
        self,
        server_id: str,
        uri: str,
    ) -> dict[str, Any]:
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")

        request = MCPRequest(
            method=MCPMethod.RESOURCES_READ,
            params={"uri": uri},
        )

        response = await self._send_request(connection, request)

        if response.error:
            raise RuntimeError(f"Resource read failed: {response.error}")

        return response.result

    # Prompt methods
    async def list_prompts(self, server_id: str) -> list[MCPPrompt]:
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")
        return list(connection.prompts)

    async def get_prompt(
        self,
        server_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        connection = self._connections.get(server_id)
        if not connection:
            raise ValueError(f"Server not connected: {server_id}")

        request = MCPRequest(
            method=MCPMethod.PROMPTS_GET,
            params={"name": name, "arguments": arguments or {}},
        )

        response = await self._send_request(connection, request)

        if response.error:
            raise RuntimeError(f"Prompt get failed: {response.error}")

        return response.result

    def get_connection(self, server_id: str) -> MCPConnection | None:
        """Get connection info."""
        return self._connections.get(server_id)

    def list_connections(self) -> dict[str, MCPConnection]:
        """List all connections."""
        return dict(self._connections)


class MCPClientManager:
    """High-level manager for MCP client with persistence."""

    def __init__(self, config_dir: Path | str = ".zksato/mcp") -> None:
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.client = MCPClient()
        self._server_configs: dict[str, MCPServerConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """Load server configurations from disk."""
        config_file = self.config_dir / "servers.json"
        if config_file.exists():
            try:
                with config_file.open("r") as f:
                    data = json.load(f)
                for s_data in data.get("servers", []):
                    config = MCPServerConfig(
                        server_id=s_data["server_id"],
                        name=s_data["name"],
                        transport=TransportType(s_data["transport"]),
                        command=s_data.get("command"),
                        cwd=Path(s_data["cwd"]) if s_data.get("cwd") else None,
                        env=s_data.get("env"),
                        url=s_data.get("url"),
                        headers=s_data.get("headers", {}),
                        timeout_seconds=s_data.get("timeout_seconds", 30.0),
                        retry_attempts=s_data.get("retry_attempts", 3),
                        retry_delay_seconds=s_data.get("retry_delay_seconds", 1.0),
                        required_capabilities=MCPCapabilities.from_dict(
                            s_data.get("required_capabilities", {})
                        ),
                        auto_connect=s_data.get("auto_connect", True),
                    )
                    self._server_configs[config.server_id] = config
            except Exception as exc:
                logger.warning("Failed to load MCP configs: %s", exc)

    def _save_configs(self) -> None:
        """Save server configurations to disk."""
        config_file = self.config_dir / "servers.json"
        try:
            data = {
                "servers": [
                    {
                        "server_id": c.server_id,
                        "name": c.name,
                        "transport": c.transport.value,
                        "command": c.command,
                        "cwd": str(c.cwd) if c.cwd else None,
                        "env": c.env,
                        "url": c.url,
                        "headers": c.headers,
                        "timeout_seconds": c.timeout_seconds,
                        "retry_attempts": c.retry_attempts,
                        "retry_delay_seconds": c.retry_delay_seconds,
                        "required_capabilities": c.required_capabilities.to_dict(),
                        "auto_connect": c.auto_connect,
                    }
                    for c in self._server_configs.values()
                ]
            }
            with config_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save MCP configs: %s", exc)

    def add_server(self, config: MCPServerConfig) -> None:
        """Add a server configuration."""
        self._server_configs[config.server_id] = config
        self._save_configs()

    def remove_server(self, server_id: str) -> bool:
        """Remove a server configuration."""
        if server_id in self._server_configs:
            del self._server_configs[server_id]
            self._save_configs()
            return True
        return False

    def get_server_config(self, server_id: str) -> MCPServerConfig | None:
        """Get server configuration."""
        return self._server_configs.get(server_id)

    def list_server_configs(self) -> list[MCPServerConfig]:
        """List all server configurations."""
        return list(self._server_configs.values())

    async def connect_server(self, server_id: str) -> MCPConnection | None:
        """Connect to a configured server."""
        config = self._server_configs.get(server_id)
        if not config:
            return None
        return await self.client.connect_server(config)

    async def connect_all_auto(self) -> dict[str, MCPConnection]:
        """Connect to all auto-connect servers."""
        results = {}
        for config in self._server_configs.values():
            if config.auto_connect:
                try:
                    conn = await self.client.connect_server(config)
                    results[config.server_id] = conn
                except Exception as exc:
                    logger.error("Failed to auto-connect %s: %s", config.server_id, exc)
        return results

    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from a server."""
        return await self.client.disconnect_server(server_id)

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        await self.client.disconnect_all()

    def get_client(self) -> MCPClient:
        """Get the underlying MCP client."""
        return self.client
