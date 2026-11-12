"""Tool registry for trading tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, create_model


class ToolContext:
    """Context for tool execution."""
    def __init__(
        self,
        account_id: str,
        session_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.account_id = account_id
        self.session_id = session_id
        self.correlation_id = correlation_id


class ToolResult(BaseModel):
    """Result of tool execution."""
    success: bool
    data: Any = None
    error: str | None = None


class TradingTool(Protocol):
    """Protocol for trading tools."""
    name: str
    description: str
    parameters: type[BaseModel]
    required_approval: str  # "none", "risk", "manual"
    
    async def execute(self, params: BaseModel, ctx: ToolContext) -> ToolResult: ...


@dataclass
class ToolRegistry:
    """Registry for trading tools."""
    
    _tools: dict[str, TradingTool] = None
    _schemas: dict[str, type[BaseModel]] = None
    
    def __post_init__(self):
        if self._tools is None:
            self._tools = {}
        if self._schemas is None:
            self._schemas = {}
    
    def register(self, tool: TradingTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        self._schemas[tool.name] = tool.parameters
    
    def get(self, name: str) -> TradingTool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_schema(self, name: str) -> dict[str, Any]:
        """Get JSON schema for a tool."""
        if name not in self._schemas:
            return {}
        return self._schemas[name].model_json_schema()
    
    def list_tools(self) -> list[dict[str, str]]:
        """List all tools."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]
    
    async def execute(
        self,
        name: str,
        params: dict[str, Any],
        ctx: ToolContext,
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {name}")
        
        validated = tool.parameters(**params)
        return await tool.execute(validated, ctx)


# Built-in tools
class GetQuoteParams(BaseModel):
    symbol: str


class GetQuoteTool:
    name = "get_quote"
    description = "Get real-time quote for a symbol"
    parameters = GetQuoteParams
    required_approval = "none"
    
    async def execute(self, params: GetQuoteParams, ctx: ToolContext) -> ToolResult:
        # Would call market data feed
        return ToolResult(success=True, data={"symbol": params.symbol, "price": 100.0})


class PlaceOrderParams(BaseModel):
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: float
    order_type: str = "LIMIT"
    price: float | None = None


class PlaceOrderTool:
    name = "place_order"
    description = "Place a trading order"
    parameters = PlaceOrderParams
    required_approval = "risk"
    
    async def execute(self, params: PlaceOrderParams, ctx: ToolContext) -> ToolResult:
        # Would call broker adapter after risk check
        return ToolResult(success=True, data={"order_id": "simulated", "symbol": params.symbol})


class GetPositionsParams(BaseModel):
    pass


class GetPositionsTool:
    name = "get_positions"
    description = "Get current positions"
    parameters = GetPositionsParams
    required_approval = "none"
    
    async def execute(self, params: GetPositionsParams, ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True, data={"positions": []})


class CancelOrderParams(BaseModel):
    order_id: str


class CancelOrderTool:
    name = "cancel_order"
    description = "Cancel an order"
    parameters = CancelOrderParams
    required_approval = "risk"
    
    async def execute(self, params: CancelOrderParams, ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True, data={"cancelled": True, "order_id": params.order_id})


class CheckRiskParams(BaseModel):
    symbol: str
    side: str
    quantity: float
    price: float | None = None


class CheckRiskTool:
    name = "check_risk"
    description = "Check risk for an order"
    parameters = CheckRiskParams
    required_approval = "none"
    
    async def execute(self, params: CheckRiskParams, ctx: ToolContext) -> ToolResult:
        # Would call risk engine
        return ToolResult(success=True, data={"allowed": True, "reason": "OK"})