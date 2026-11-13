"""LLM client factory for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato_api.llm_clients.gemini4_hydrogen import (
    Gemini4HydrogenClient,
    Gemini4HydrogenConfig,
    HydrogenThinkingLevel,
)
from zksato_api.llm_clients.local_llama_server import (
    LocalLLMServerConfig,
    LocalLLMServerManager,
)
from zksato_api.llm_clients.local_llm import (
    LocalLLMBackend,
    LocalLLMClient,
    LocalLLMConfig,
)


@dataclass
class LLMClientFactory:
    """Factory for LLM clients.

    Supports OpenAI, Anthropic, Gemini, Gemini 4 Hydrogen, and local LLM
    providers. Local LLM backends (Ollama, llama.cpp, vLLM, TGI) expose
    an OpenAI-compatible API and keep all data on-premise — critical for
    zksato's paper/sandbox trading environments.
    """

    def create_client(self, provider: str, **kwargs: Any) -> Any:
        """Create an LLM client for the given provider.

        Args:
            provider: Provider name (openai, anthropic, gemini,
                gemini-4-hydrogen, local-llm).
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
        if provider == "local-llm":
            local_config = LocalLLMConfig(**kwargs)
            return LocalLLMClient(config=local_config)
        # Would create OpenAI, Anthropic, etc. clients
        return None

    def get_available_providers(self) -> list[str]:
        """Get available LLM providers."""
        return [
            "openai",
            "anthropic",
            "gemini",
            "gemini-4-hydrogen",
            "local-llm",
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

    def create_local_llm_client(
        self,
        backend: LocalLLMBackend = LocalLLMBackend.OLLAMA,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        api_key: str | None = None,
    ) -> LocalLLMClient:
        """Create a local LLM client for offline inference.

        Convenience method for agentic workflows that need local LLM
        inference without external API calls — keeping all data on-premise.
        """
        config = LocalLLMConfig(
            backend=backend,
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
        return LocalLLMClient(config=config)

    def create_local_llama_server(
        self,
        config: LocalLLMServerConfig | None = None,
    ) -> LocalLLMServerManager:
        """Create a local LLM server manager for offline inference.

        Convenience method for agentic workflows that need a locally-hosted
        LLM server (e.g., llama.cpp) without external API calls — keeping
        all data on-premise.

        Args:
            config: LocalLLMServerConfig with server settings. If None,
                a default config is used.

        Returns:
            LocalLLMServerManager instance
        """
        if config is None:
            config = LocalLLMServerConfig()
        return LocalLLMServerManager(config=config)
