"""Gemini 4 Hydrogen LLM client for agentic workflows.

Gemini 4 Hydrogen is Google's daily driver model for agentic workflows,
optimized for rapid execution across coding, testing, and verification tasks.
Supports four thinking levels (low, medium, high, xhigh) with a 1M token
context window and built-in safety for agentic execution.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HydrogenThinkingLevel(StrEnum):
    """Gemini 4 Hydrogen thinking levels.

    Scales quality, latency, and cost in a smooth progression.
    Only wait and pay for the reasoning depth a task requires.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


@dataclass
class Gemini4HydrogenConfig:
    """Configuration for Gemini 4 Hydrogen client."""

    api_key: str | None = None
    model: str = "gemini-4-hydrogen"
    thinking_level: HydrogenThinkingLevel = HydrogenThinkingLevel.HIGH
    max_input_tokens: int = 1_000_000
    max_output_tokens: int = 1_000_000
    temperature: float = 0.7
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


@dataclass
class LLMResponse:
    """Structured LLM response."""

    content: str
    model: str
    thinking_level: HydrogenThinkingLevel
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    finish_reason: str
    safety_ratings: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Gemini4HydrogenClient:
    """Gemini 4 Hydrogen client for agentic workflows.

    Provides fast, disciplined execution for coding, testing, and verification
    tasks. Designed to work standalone or paired with Gemini 4 Carbon/Argon
    in multi-model orchestrator workflows.
    """

    def __init__(self, config: Gemini4HydrogenConfig | None = None) -> None:
        self.config = config or Gemini4HydrogenConfig()
        self._http_client: Any = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._initialized:
            return
        try:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
        except ImportError:
            logger.warning("httpx not installed; client will operate in stub mode")
        self._initialized = True

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
        self._initialized = False

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        thinking_level: HydrogenThinkingLevel | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> dict[str, Any]:
        """Build the API request payload for Gemini 4 Hydrogen."""
        level = thinking_level or self.config.thinking_level
        return {
            "model": self.config.model,
            "messages": messages,
            "thinking_level": level.value,
            "temperature": self.config.temperature,
            "max_input_tokens": self.config.max_input_tokens,
            "max_output_tokens": self.config.max_output_tokens,
            **kwargs,
        }

    def _parse_response(self, raw: dict[str, Any], level: HydrogenThinkingLevel) -> LLMResponse:
        """Parse the API response into a structured LLMResponse."""
        choices = raw.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
        else:
            content = raw.get("content", "")

        usage = raw.get("usage", {})
        return LLMResponse(
            content=content,
            model=self.config.model,
            thinking_level=level,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_seconds=raw.get("latency_seconds", 0.0),
            finish_reason=raw.get("finish_reason", "stop"),
            safety_ratings=raw.get("safety_ratings", {}),
            metadata=raw.get("metadata", {}),
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        thinking_level: HydrogenThinkingLevel | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> LLMResponse:
        """Generate a response using Gemini 4 Hydrogen.

        Args:
            messages: Chat messages in OpenAI-compatible format.
            thinking_level: Override the default thinking level for this call.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Structured LLMResponse with content, token counts, and metadata.

        Raises:
            RuntimeError: If the client is not initialized.
            ValueError: If the API returns an error.
        """
        if not self._initialized:
            await self.initialize()

        level = thinking_level or self.config.thinking_level
        payload = self._build_payload(messages, level, **kwargs)

        # Stub mode when httpx is not available or no API key
        if not self._http_client or not self.config.api_key:
            logger.info(
                "Gemini 4 Hydrogen stub mode: generating synthetic response",
            )
            return LLMResponse(
                content=(
                    f"[Gemini 4 Hydrogen stub] Thinking level: {level.value}. "
                    "No API key configured. Set GEMINI_API_KEY for live calls."
                ),
                model=self.config.model,
                thinking_level=level,
                input_tokens=sum(len(m.get("content", "")) for m in messages) // 4,
                output_tokens=50,
                latency_seconds=0.1,
                finish_reason="stop",
                metadata={"stub": True},
            )

        start = datetime.now(UTC)
        last_error: Exception | None = None
        response: LLMResponse | None = None
        for attempt in range(self.config.max_retries):
            try:
                resp = await self._http_client.post(
                    "https://generativelanguage.googleapis.com/v1/models/gemini-4-hydrogen:generateContent",
                    json=payload,
                )
                resp.raise_for_status()
                raw = resp.json()
                latency = (datetime.now(UTC) - start).total_seconds()
                response = self._parse_response(raw, level)
                response.latency_seconds = latency
                break
            except Exception as exc:
                last_error = exc
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay_seconds * (2**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)
        if response is None:
            raise RuntimeError(
                "Gemini 4 Hydrogen API failed after "
                f"{self.config.max_retries} attempts: {last_error}"
            )
        return response

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        thinking_level: HydrogenThinkingLevel = HydrogenThinkingLevel.HIGH,
    ) -> LLMResponse:
        """Generate code with Gemini 4 Hydrogen.

        Optimized for coding tasks — produces clean, production-ready code
        without rewriting unrelated files.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert software engineer. Write clean, "
                    f"production-ready {language} code. Focus on surgical edits "
                    "without rewriting unrelated files. Include type hints, "
                    "docstrings, and error handling."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        return await self.generate(messages, thinking_level=thinking_level)

    async def analyze_code(
        self,
        code: str,
        language: str = "python",
        thinking_level: HydrogenThinkingLevel = HydrogenThinkingLevel.XHIGH,
    ) -> LLMResponse:
        """Analyze code for bugs, security issues, and improvements.

        Uses xhigh thinking for deep analysis of complex codebases.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior code reviewer. Analyze the provided "
                    f"{language} code for bugs, security vulnerabilities, "
                    "performance issues, and maintainability concerns. "
                    "Provide specific, actionable recommendations."
                ),
            },
            {"role": "user", "content": f"Code to analyze:\n\n```{language}\n{code}\n```"},
        ]
        return await self.generate(messages, thinking_level=thinking_level)

    async def verify_test(
        self,
        test_code: str,
        source_code: str,
        thinking_level: HydrogenThinkingLevel = HydrogenThinkingLevel.HIGH,
    ) -> LLMResponse:
        """Verify that tests adequately cover the source code.

        Returns pass/fail assessment with gap analysis.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a test verification engineer. Compare the test code "
                    "against the source code and determine if the tests adequately "
                    "cover all branches, edge cases, and error conditions. "
                    "Report pass/fail with specific gap analysis."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source code:\n```python\n{source_code}\n```\n\n"
                    f"Test code:\n```python\n{test_code}\n```"
                ),
            },
        ]
        return await self.generate(messages, thinking_level=thinking_level)

    def get_info(self) -> dict[str, Any]:
        """Get client information and capabilities."""
        return {
            "model": self.config.model,
            "provider": "google",
            "thinking_levels": [level.value for level in HydrogenThinkingLevel],
            "default_thinking_level": self.config.thinking_level.value,
            "max_input_tokens": self.config.max_input_tokens,
            "max_output_tokens": self.config.max_output_tokens,
            "capabilities": [
                "code_generation",
                "code_analysis",
                "test_verification",
                "agentic_workflows",
                "multi_model_orchestration",
            ],
            "initialized": self._initialized,
        }
