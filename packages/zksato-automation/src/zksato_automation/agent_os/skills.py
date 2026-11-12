"""Skill registry for agent OS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from zksato_api.llm_clients import HydrogenThinkingLevel  # type: ignore[import-untyped]


class TradingSkill(Protocol):
    """Protocol for trading skills."""

    name: str
    description: str
    required_capabilities: set[str]

    async def execute(self, params: Any, ctx: SkillContext) -> SkillResult: ...


@dataclass
class SkillContext:
    """Context for skill execution."""

    account_id: str
    subaccount_id: str | None = None


@dataclass
class SkillResult:
    """Result of skill execution."""

    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class SkillRegistry:
    """Registry for trading skills."""

    _skills: dict[str, TradingSkill] = None

    def __post_init__(self):
        if self._skills is None:
            self._skills = {}

    def register(self, skill: TradingSkill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill

    def get(self, name: str) -> TradingSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        """List all skills."""
        return [{"name": s.name, "description": s.description} for s in self._skills.values()]


# Built-in skills
class GetQuoteSkill:
    name = "get_quote"
    description = "Get real-time quote for a symbol"
    required_capabilities = {"realtime_quotes"}

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        symbol = params.get("symbol")
        if not symbol:
            return SkillResult(success=False, error="symbol required")
        # Would call market data feed
        return SkillResult(success=True, data={"symbol": symbol, "price": 100.0})


class PlaceOrderSkill:
    name = "place_order"
    description = "Place a trading order"
    required_capabilities = {"order_management"}

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        symbol = params.get("symbol")
        side = params.get("side")
        quantity = params.get("quantity")
        if not all([symbol, side, quantity]):
            return SkillResult(success=False, error="symbol, side, quantity required")
        # Would call broker adapter
        return SkillResult(success=True, data={"order_id": "simulated", "symbol": symbol})


class GetPositionsSkill:
    name = "get_positions"
    description = "Get current positions"
    required_capabilities = {"position_tracking"}

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        # Would call portfolio manager
        return SkillResult(success=True, data={"positions": []})


class CancelOrderSkill:
    name = "cancel_order"
    description = "Cancel an order"
    required_capabilities = {"order_management"}

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        order_id = params.get("order_id")
        if not order_id:
            return SkillResult(success=False, error="order_id required")
        return SkillResult(success=True, data={"cancelled": True, "order_id": order_id})


# LLM-powered skills (require Gemini 4 Hydrogen client)
class CodeGenerationSkill:
    """Generate code using Gemini 4 Hydrogen."""

    name = "generate_code"
    description = "Generate production-ready code using Gemini 4 Hydrogen"
    required_capabilities = {"code_generation", "llm"}

    def __init__(self, llm_client: Any = None) -> None:  # noqa: ANN401
        self.llm_client = llm_client
    
    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        prompt = params.get("prompt")
        language = params.get("language", "python")
        thinking_level = params.get("thinking_level", "high")

        if not prompt:
            return SkillResult(success=False, error="prompt required")

        if self.llm_client is None:
            return SkillResult(
                success=False,
                error="LLM client not configured. Set GEMINI_API_KEY and initialize client.",
            )

        try:
            level = HydrogenThinkingLevel(thinking_level)
        except ValueError:
            level = HydrogenThinkingLevel.HIGH

        response = await self.llm_client.generate_code(
            prompt=prompt,
            language=language,
            thinking_level=level,
        )

        return SkillResult(
            success=True,
            data={
                "code": response.content,
                "model": response.model,
                "thinking_level": response.thinking_level.value,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_seconds": response.latency_seconds,
            },
        )


class CodeAnalysisSkill:
    """Analyze code using Gemini 4 Hydrogen."""

    name = "analyze_code"
    description = "Analyze code for bugs, security, and performance using Gemini 4 Hydrogen"
    required_capabilities = {"code_analysis", "llm"}

    def __init__(self, llm_client: Any = None) -> None:  # noqa: ANN401
        self.llm_client = llm_client

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        code = params.get("code")
        language = params.get("language", "python")
        thinking_level = params.get("thinking_level", "xhigh")

        if not code:
            return SkillResult(success=False, error="code required")

        if self.llm_client is None:
            return SkillResult(
                success=False,
                error="LLM client not configured. Set GEMINI_API_KEY and initialize client.",
            )

        try:
            level = HydrogenThinkingLevel(thinking_level)
        except ValueError:
            level = HydrogenThinkingLevel.XHIGH

        response = await self.llm_client.analyze_code(
            code=code,
            language=language,
            thinking_level=level,
        )

        return SkillResult(
            success=True,
            data={
                "analysis": response.content,
                "model": response.model,
                "thinking_level": response.thinking_level.value,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_seconds": response.latency_seconds,
            },
        )


class TestVerificationSkill:
    """Verify test coverage using Gemini 4 Hydrogen."""

    name = "verify_test"
    description = "Verify test coverage using Gemini 4 Hydrogen"
    required_capabilities = {"test_verification", "llm"}

    def __init__(self, llm_client: Any = None) -> None:  # noqa: ANN401
        self.llm_client = llm_client

    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        test_code = params.get("test_code")
        source_code = params.get("source_code")
        thinking_level = params.get("thinking_level", "high")

        if not test_code or not source_code:
            return SkillResult(success=False, error="test_code and source_code required")

        if self.llm_client is None:
            return SkillResult(
                success=False,
                error="LLM client not configured. Set GEMINI_API_KEY and initialize client.",
            )

        try:
            level = HydrogenThinkingLevel(thinking_level)
        except ValueError:
            level = HydrogenThinkingLevel.HIGH

        response = await self.llm_client.verify_test(
            test_code=test_code,
            source_code=source_code,
            thinking_level=level,
        )

        return SkillResult(
            success=True,
            data={
                "verification": response.content,
                "model": response.model,
                "thinking_level": response.thinking_level.value,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_seconds": response.latency_seconds,
            },
        )
