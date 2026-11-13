"""MCP (Model Context Protocol) module for ZKSATO."""

from .client import (
    MCPClient,
    MCPClientManager,
    MCPConnection,
)
from .client import (
    MCPServerConfig as MCPServerConnectionConfig,
)
from .protocol import (
    MCPCapabilities,
    MCPClientInfo,
    MCPErrorCode,
    MCPMethod,
    MCPNotification,
    MCPPrompt,
    MCPRequest,
    MCPResource,
    MCPResourceTemplate,
    MCPResponse,
    MCPServerInfo,
    MCPTool,
    MCPTransport,
    SSETransport,
    StdioTransport,
    TransportType,
    WebSocketTransport,
)
from .server import (
    MCPServer,
    MCPServerConfig,
    StdioServerTransport,
    run_stdio_server,
)

__all__ = [
    # Protocol
    "MCPCapabilities",
    # Client
    "MCPClient",
    "MCPClientInfo",
    "MCPClientManager",
    "MCPConnection",
    "MCPErrorCode",
    "MCPMethod",
    "MCPNotification",
    "MCPPrompt",
    "MCPRequest",
    "MCPResource",
    "MCPResourceTemplate",
    "MCPResponse",
    # Server
    "MCPServer",
    "MCPServerConfig",
    "MCPServerConnectionConfig",
    "MCPServerInfo",
    "MCPTool",
    "MCPTransport",
    "SSETransport",
    "StdioServerTransport",
    "StdioTransport",
    "TransportType",
    "WebSocketTransport",
    "run_stdio_server",
]
