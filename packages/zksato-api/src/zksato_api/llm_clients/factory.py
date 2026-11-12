"""LLM client factory for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMClientFactory:
    """Factory for LLM clients."""
    
    def create_client(self, provider: str, **kwargs) -> Any:
        """Create an LLM client."""
        # Would create OpenAI, Anthropic, etc. clients
        return None
    
    def get_available_providers(self) -> list[str]:
        """Get available providers."""
        return ["openai", "anthropic", "gemini"]