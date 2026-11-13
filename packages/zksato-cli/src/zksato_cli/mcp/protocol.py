"""MCP (Model Context Protocol) implementation for ZKSATO.

Implements the Model Context Protocol specification for:
- Server discovery and connection management
- Tool discovery and execution
- Resource discovery and access
- Prompt discovery and rendering
- Capability negotiation
- Transport abstraction (stdio, SSE, WebSocket)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MCPErrorCode(int, Enum):
    """MCP error codes per specification."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000
    CONNECTION_CLOSED = -32001
    REQUEST_CANCELLED = -32002


class MCPMethod(str, Enum):
    """MCP protocol methods."""

    # Lifecycle
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    SHUTDOWN = "shutdown"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    RESOURCES_TEMPLATES_LIST = "resources/templates/list"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"
    LOGGING_MESSAGE = "notifications/message"

    # Completion
    COMPLETION_COMPLETE = "completion/complete"


class TransportType(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"
    HTTP = "http"


@dataclass
class MCPCapabilities:
    """Server/client capabilities."""

    # Server capabilities
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    logging: bool = False
    completions: bool = False

    # Resource capabilities
    resources_subscribe: bool = False
    resources_list_changed: bool = False

    # Prompt capabilities
    prompts_list_changed: bool = False

    # Client capabilities
    sampling: bool = False
    roots: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tools": self.tools,
            "resources": self.resources,
            "prompts": self.prompts,
            "logging": self.logging,
            "completions": self.completions,
            "resourcesSubscribe": self.resources_subscribe,
            "resourcesListChanged": self.resources_list_changed,
            "promptsListChanged": self.prompts_list_changed,
            "sampling": self.sampling,
            "roots": self.roots,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPCapabilities:
        return cls(
            tools=data.get("tools", False),
            resources=data.get("resources", False),
            prompts=data.get("prompts", False),
            logging=data.get("logging", False),
            completions=data.get("completions", False),
            resources_subscribe=data.get("resourcesSubscribe", False),
            resources_list_changed=data.get("resourcesListChanged", False),
            prompts_list_changed=data.get("promptsListChanged", False),
            sampling=data.get("sampling", False),
            roots=data.get("roots", False),
        )


@dataclass
class MCPServerInfo:
    """Server information from initialize."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)
    instructions: str | None = None


@dataclass
class MCPClientInfo:
    """Client information for initialize."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)


@dataclass
class MCPTool:
    """MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str | None = None
    annotations: dict[str, Any] | None = None


@dataclass
class MCPResourceTemplate:
    """MCP resource template."""

    uri_template: str
    name: str
    description: str | None = None
    mime_type: str | None = None


@dataclass
class MCPPrompt:
    """MCP prompt definition."""

    name: str
    description: str | None = None
    arguments: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MCPRequest:
    """MCP JSON-RPC request."""

    jsonrpc: str = "2.0"
    id: str | int | None = field(default_factory=lambda: str(uuid.uuid4()))
    method: str = ""
    params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.id is not None:
            result["id"] = self.id
        if self.params is not None:
            result["params"] = self.params
        return result


@dataclass
class MCPResponse:
    """MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: dict[str, Any] | None = None

    @classmethod
    def success(cls, id: str | int | None, result: Any) -> MCPResponse:
        return cls(id=id, result=result)

    @classmethod
    def make_error(
        cls, id: str | int | None, code: int, message: str, data: Any = None
    ) -> MCPResponse:
        """Build an error response (named to avoid clashing with the `error` field)."""
        err = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        return cls(id=id, error=err)

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class MCPNotification:
    """MCP JSON-RPC notification."""

    jsonrpc: str = "2.0"
    method: str = ""
    params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        return result


class MCPTransport(ABC):
    """Abstract transport for MCP communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    async def send(self, message: dict[str, Any]) -> None:
        """Send a message."""
        pass

    @abstractmethod
    async def receive(self) -> dict[str, Any] | None:
        """Receive a message."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected."""
        pass


class StdioTransport(MCPTransport):
    """Standard I/O transport for MCP."""

    def __init__(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.cwd = cwd or Path()
        self.env = env or {}
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False

    async def connect(self) -> None:
        """Start subprocess and connect stdio."""
        env = {**os.environ, **self.env}
        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=self.cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader = self._process.stdout
        self._writer = self._process.stdin
        self._connected = True
        logger.info("Stdio transport connected: %s", self.command)

    async def disconnect(self) -> None:
        """Terminate subprocess."""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
        self._connected = False
        logger.info("Stdio transport disconnected")

    async def send(self, message: dict[str, Any]) -> None:
        """Send message via stdin."""
        if not self._writer:
            raise RuntimeError("Not connected")
        data = json.dumps(message) + "\n"
        self._writer.write(data.encode())
        await self._writer.drain()

    async def receive(self) -> dict[str, Any] | None:
        """Receive message from stdout."""
        if not self._reader:
            return None
        line = await self._reader.readline()
        if not line:
            return None
        try:
            return json.loads(line.decode().strip())
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode MCP message: %s", exc)
            return None

    async def is_connected(self) -> bool:
        return self._connected and self._process and self._process.returncode is None


class SSETransport(MCPTransport):
    """Server-Sent Events transport for MCP."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._session: aiohttp.ClientSession | None = None
        self._response: aiohttp.ClientResponse | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to SSE endpoint."""
        import aiohttp

        self._session = aiohttp.ClientSession()
        self._response = await self._session.get(
            self.url,
            headers={"Accept": "text/event-stream", **self.headers},
        )
        self._connected = True
        logger.info("SSE transport connected: %s", self.url)

    async def disconnect(self) -> None:
        """Close SSE connection."""
        if self._response:
            self._response.close()
        if self._session:
            await self._session.close()
        self._connected = False
        logger.info("SSE transport disconnected")

    async def send(self, message: dict[str, Any]) -> None:
        """Send via HTTP POST (SSE is typically one-way)."""
        if not self._session:
            raise RuntimeError("Not connected")
        async with self._session.post(
            self.url,
            json=message,
            headers={"Content-Type": "application/json", **self.headers},
        ) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Send failed: {resp.status}")

    async def receive(self) -> dict[str, Any] | None:
        """Receive SSE event."""
        if not self._response:
            return None
        async for line in self._response.content:
            line = line.decode().strip()
            if line.startswith("data: "):
                try:
                    return json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
        return None

    async def is_connected(self) -> bool:
        return self._connected and self._response and not self._response.closed


class WebSocketTransport(MCPTransport):
    """WebSocket transport for MCP."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect via WebSocket."""
        import aiohttp

        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(
            self.url,
            headers=self.headers,
        )
        self._connected = True
        logger.info("WebSocket transport connected: %s", self.url)

    async def disconnect(self) -> None:
        """Close WebSocket."""
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        self._connected = False
        logger.info("WebSocket transport disconnected")

    async def send(self, message: dict[str, Any]) -> None:
        """Send via WebSocket."""
        if not self._ws:
            raise RuntimeError("Not connected")
        await self._ws.send_json(message)

    async def receive(self) -> dict[str, Any] | None:
        """Receive WebSocket message."""
        if not self._ws:
            return None
        msg = await self._ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                return json.loads(msg.data)
            except json.JSONDecodeError:
                return None
        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
            self._connected = False
        return None

    async def is_connected(self) -> bool:
        return self._connected and self._ws and not self._ws.closed


# Optional HTTP/WebSocket dependency; transports degrade gracefully when absent
try:
    import aiohttp
except ImportError:
    aiohttp = None
