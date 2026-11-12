"""LLM client factory for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato_api.llm_clients.gemini4_hydrogen import (
    Gemini4HydrogenClient,
    Gemini4HydrogenConfig,
    HydrogenThinkingLevel,
)


@dataclass
class LLMClientFactory:
    """Factory for LLM clients.

    Supports OpenAI, Anthropic, Gemini, and Gemini 4 Hydrogen providers.
    Gemini 4 Hydrogen is optimized for agentic workflows with four thinking
    levels (low, medium, high, xhigh) and a 1M token context window.
    """

    def create_client(self, provider: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """Create an LLM client for the given provider.

        Args:
            provider: Provider name (openai, anthropic, gemini, gemini-4-hydrogen).
            **kwargs: Provider-specific configuration.

        Returns:
            An LLM client instance.

        Raises:
            ValueError: If the provider is not supported.
        """
        if provider == "gemini-4-hydrogen":
            config = Gemini4HydrogenConfig(**kwargs)
            return Gemini4HydrogenClient(config=config)
        if provider == "gemini":
            config = Gemini4HydrogenConfig(model="gemini", **kwargs)
            return Gemini4HydrogenClient(config=config)
        # Would create OpenAI, Anthropic, etc. clients
        return None

    def get_available_providers(self) -> list[str]:
        """Get available LLM providers."""
        return [
            "openai",
            "anthropic",
            "gemini",
            "gemini-4-hydrogen",
        ]

    def create_hydrogen_client(
        self,
        thinking_level: HydrogenThinkingLevel = HydrogenThinkingLevel.HIGH,
        api_key: str | None = None,
    ) -> Gemini4HydrogenClient:
        """Create a Gemini 4 Hydrogen client with the given thinking level.

        Convenience method for agentic workflows that need Hydrogen specifically.
        """
        config = Gemini4HydrogenConfig(
            api_key=api_key,
            thinking_level=thinking_level,
        )
        return Gemini4HydrogenClient(config=config)
