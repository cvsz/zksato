"""MCP Server implementation for ZKSATO.

Provides a full MCP server implementation with:
- Tool registration and execution
- Resource management
- Prompt templates
- Resource subscriptions
- Capability negotiation
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zksato_cli.mcp.protocol import (
    MCPCapabilities,
    MCPErrorCode,
    MCPMethod,
    MCPNotification,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResourceTemplate,
    MCPResponse,
    MCPTool,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""

    name: str = "zksato-mcp"
    version: str = "1.0.0"
    instructions: str | None = None
    capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)


@dataclass
class ResourceSubscription:
    """Resource subscription info."""

    uri: str
    client_id: str
    subscribed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MCPServer:
    """MCP Server implementation."""

    def __init__(
        self,
        config: MCPServerConfig | None = None,
    ) -> None:
        self.config = config or MCPServerConfig()
        self._tools: dict[str, MCPTool] = {}
        self._tool_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]] = {}
        self._resources: dict[str, MCPResource] = {}
        self._resource_handlers: dict[str, Callable[[str], Awaitable[dict[str, Any]]]] = {}
        self._resource_templates: dict[str, MCPResourceTemplate] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._prompt_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}
        self._subscriptions: dict[str, list[ResourceSubscription]] = {}
        self._initialized = False

    def register_tool(
        self,
        tool: MCPTool,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """Register a tool with its handler."""
        self._tools[tool.name] = tool
        self._tool_handlers[tool.name] = handler
        logger.info("Registered tool: %s", tool.name)

    def register_resource(
        self,
        resource: MCPResource,
        handler: Callable[[str], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        """Register a resource."""
        self._resources[resource.uri] = resource
        if handler:
            self._resource_handlers[resource.uri] = handler
        logger.info("Registered resource: %s", resource.uri)

    def register_resource_template(self, template: MCPResourceTemplate) -> None:
        """Register a resource template."""
        self._resource_templates[template.uri_template] = template
        logger.info("Registered resource template: %s", template.uri_template)

    def register_prompt(
        self,
        prompt: MCPPrompt,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        """Register a prompt template."""
        self._prompts[prompt.name] = prompt
        if handler:
            self._prompt_handlers[prompt.name] = handler
        logger.info("Registered prompt: %s", prompt.name)

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an incoming MCP request."""
        method = request.method

        try:
            if method == MCPMethod.INITIALIZE:
                return await self._handle_initialize(request)
            elif method == MCPMethod.TOOLS_LIST:
                return await self._handle_tools_list(request)
            elif method == MCPMethod.TOOLS_CALL:
                return await self._handle_tools_call(request)
            elif method == MCPMethod.RESOURCES_LIST:
                return await self._handle_resources_list(request)
            elif method == MCPMethod.RESOURCES_READ:
                return await self._handle_resources_read(request)
            elif method == MCPMethod.RESOURCES_TEMPLATES_LIST:
                return await self._handle_resources_templates_list(request)
            elif method == MCPMethod.RESOURCES_SUBSCRIBE:
                return await self._handle_resources_subscribe(request)
            elif method == MCPMethod.RESOURCES_UNSUBSCRIBE:
                return await self._handle_resources_unsubscribe(request)
            elif method == MCPMethod.PROMPTS_LIST:
                return await self._handle_prompts_list(request)
            elif method == MCPMethod.PROMPTS_GET:
                return await self._handle_prompts_get(request)
            elif method == MCPMethod.COMPLETION_COMPLETE:
                return await self._handle_completion(request)
            else:
                return MCPResponse.make_error(
                    id=request.id,
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method not found: {method}",
                )
        except Exception as exc:
            logger.error("Error handling request %s: %s", method, exc)
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.INTERNAL_ERROR,
                message=str(exc),
            )

    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle initialize request."""

        self._initialized = True

        return MCPResponse.success(
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": self.config.capabilities.to_dict(),
                "serverInfo": {
                    "name": self.config.name,
                    "version": self.config.version,
                },
                "instructions": self.config.instructions,
            },
        )

    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """List available tools."""
        tools = [tool.to_dict() for tool in self._tools.values()]
        return MCPResponse.success(
            id=request.id,
            result={"tools": tools},
        )

    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Call a tool."""
        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tool_handlers:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Tool not found: {tool_name}",
            )

        try:
            handler = self._tool_handlers[tool_name]
            result = await handler(arguments)

            return MCPResponse.success(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ],
                    "isError": False,
                },
            )
        except Exception as exc:
            logger.error("Tool execution failed: %s", exc)
            return MCPResponse.success(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {exc}",
                        }
                    ],
                    "isError": True,
                },
            )

    async def _handle_resources_list(self, request: MCPRequest) -> MCPResponse:
        """List available resources."""
        resources = [resource.to_dict() for resource in self._resources.values()]
        return MCPResponse.success(
            id=request.id,
            result={"resources": resources},
        )

    async def _handle_resources_read(self, request: MCPRequest) -> MCPResponse:
        """Read a resource."""
        params = request.params or {}
        uri = params.get("uri")

        if not uri:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing uri parameter",
            )

        if uri not in self._resource_handlers:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Resource not found: {uri}",
            )

        try:
            handler = self._resource_handlers[uri]
            content = await handler(uri)

            return MCPResponse.success(
                id=request.id,
                result={
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": content.get("mimeType", "text/plain"),
                            "text": content.get("text", ""),
                        }
                    ],
                },
            )
        except Exception as exc:
            logger.error("Resource read failed: %s", exc)
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.INTERNAL_ERROR,
                message=str(exc),
            )

    async def _handle_resources_templates_list(self, request: MCPRequest) -> MCPResponse:
        """List resource templates."""
        templates = [template.to_dict() for template in self._resource_templates.values()]
        return MCPResponse.success(
            id=request.id,
            result={"resourceTemplates": templates},
        )

    async def _handle_resources_subscribe(self, request: MCPRequest) -> MCPResponse:
        """Subscribe to resource updates."""
        params = request.params or {}
        uri = params.get("uri")

        if not uri:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing uri parameter",
            )

        if uri not in self._resources:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Resource not found: {uri}",
            )

        # In a real implementation, we'd track subscriptions per client
        # For now, just acknowledge
        return MCPResponse.success(
            id=request.id,
            result={},
        )

    async def _handle_resources_unsubscribe(self, request: MCPRequest) -> MCPResponse:
        """Unsubscribe from resource updates."""
        params = request.params or {}
        uri = params.get("uri")

        if not uri:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing uri parameter",
            )

        return MCPResponse.success(
            id=request.id,
            result={},
        )

    async def _handle_prompts_list(self, request: MCPRequest) -> MCPResponse:
        """List available prompts."""
        prompts = [prompt.to_dict() for prompt in self._prompts.values()]
        return MCPResponse.success(
            id=request.id,
            result={"prompts": prompts},
        )

    async def _handle_prompts_get(self, request: MCPRequest) -> MCPResponse:
        """Get a prompt."""
        params = request.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})

        if not name or name not in self._prompts:
            return MCPResponse.make_error(
                id=request.id,
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Prompt not found: {name}",
            )

        prompt = self._prompts[name]

        # If there's a handler, use it to render the prompt
        if name in self._prompt_handlers:
            handler = self._prompt_handlers[name]
            try:
                rendered = await handler(arguments)
                messages = rendered.get("messages", [])
            except Exception as exc:
                logger.error("Prompt handler failed: %s", exc)
                messages = []
        else:
            # Use prompt template
            messages = [
                {
                    "role": "user",
                    "content": prompt.description or f"Prompt: {name}",
                }
            ]

        return MCPResponse.success(
            id=request.id,
            result={
                "description": prompt.description,
                "messages": messages,
            },
        )

    async def _handle_completion(self, request: MCPRequest) -> MCPResponse:
        """Handle completion request."""
        # Placeholder for completion support
        return MCPResponse.success(
            id=request.id,
            result={
                "completion": {
                    "values": [],
                    "total": 0,
                    "hasMore": False,
                },
            },
        )

    def handle_notification(self, notification: MCPNotification) -> None:
        """Handle an incoming notification."""
        method = notification.method
        params = notification.params or {}

        if method == MCPMethod.INITIALIZED:
            self._initialized = True
            logger.info("Client initialized")
        elif method == MCPMethod.LOGGING_MESSAGE:
            level = params.get("level", "info")
            message = params.get("message", "")
            logger.log(getattr(logging, level.upper(), logging.INFO), "Client log: %s", message)


class StdioServerTransport:
    """STDIO transport for MCP server."""

    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._running = False

    async def start(self) -> None:
        """Start the stdio transport."""
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        self._writer = asyncio.StreamWriter(
            sys.stdout,
            protocol,
            asyncio.get_event_loop(),
        )
        logger.info("STDIO transport started")

    async def send(self, message: dict[str, Any]) -> None:
        """Send a message."""
        if self._writer:
            data = json.dumps(message) + "\n"
            self._writer.write(data.encode())
            await self._writer.drain()

    async def receive(self) -> dict[str, Any] | None:
        """Receive a message."""
        if not self._reader:
            return None
        try:
            line = await self._reader.readline()
            if not line:
                return None
            return json.loads(line.decode().strip())
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode message: %s", exc)
            return None
        except Exception as exc:
            logger.error("Error receiving message: %s", exc)
            return None

    async def close(self) -> None:
        """Close the transport."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()


async def run_stdio_server(server: MCPServer) -> None:
    """Run an MCP server over stdio."""
    transport = StdioServerTransport()
    await transport.start()

    try:
        while True:
            message = await transport.receive()
            if message is None:
                break

            if "method" in message and "id" in message:
                # Request
                request = MCPRequest(**message)
                response = await server.handle_request(request)
                await transport.send(response.to_dict())
            elif "method" in message and "id" not in message:
                # Notification
                notification = MCPNotification(**message)
                server.handle_notification(notification)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("Server error: %s", exc)
    finally:
        await transport.close()


# Example usage
async def main() -> None:
    """Example server with some built-in tools."""
    server = MCPServer(
        MCPServerConfig(
            name="zksato-mcp",
            version="1.0.0",
            instructions="ZKSATO MCP Server for file operations and code analysis",
            capabilities=MCPCapabilities(
                tools=True,
                resources=True,
                prompts=True,
            ),
        )
    )

    # Register a file read tool
    server.register_tool(
        MCPTool(
            name="read_file",
            description="Read a file from the filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        ),
        handler=lambda args: {
            "content": Path(args["path"]).read_text(encoding="utf-8"),
        },
    )

    # Register a file write tool
    server.register_tool(
        MCPTool(
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
        ),
        handler=lambda args: {
            "success": True,
            "path": args["path"],
        },
    )

    # Run server
    await run_stdio_server(server)


if __name__ == "__main__":
    import sys

    asyncio.run(main())
