from __future__ import annotations

from typing import Any


class ProviderCapabilities:
    """Capabilities and configuration knobs for a single LLM provider.

    Attributes describe what the provider supports; settings are the
    runtime values forwarded to the client (e.g. thinking level, reasoning
    effort, output-token cap).
    """

    def __init__(
        self,
        *,
        supports_thinking: bool = False,
        supports_reasoning_effort: bool = False,
        supports_max_output_tokens: bool = False,
        supports_temperature: bool = True,
        supports_max_retries: bool = True,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.supports_thinking = supports_thinking
        self.supports_reasoning_effort = supports_reasoning_effort
        self.supports_max_output_tokens = supports_max_output_tokens
        self.supports_temperature = supports_temperature
        self.supports_max_retries = supports_max_retries
        self.settings = dict(settings or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value


# Known provider capability profiles. Unknown providers fall back to the
# default (temperature + retries only).
PROVIDER_CAPABILITIES: dict[str, ProviderCapabilities] = {
    "openai": ProviderCapabilities(
        supports_reasoning_effort=True,
        supports_max_output_tokens=True,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "reasoning_effort": None,  # "low", "medium", "high"
            "max_tokens": None,
            "temperature": None,
            "max_retries": None,
        },
    ),
    "anthropic": ProviderCapabilities(
        supports_thinking=False,
        supports_reasoning_effort=True,
        supports_max_output_tokens=True,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "effort": None,  # "low", "medium", "high"
            "max_tokens": None,
            "temperature": None,
            "max_retries": None,
        },
    ),
    "google": ProviderCapabilities(
        supports_thinking=True,
        supports_reasoning_effort=False,
        supports_max_output_tokens=True,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "thinking_level": None,  # "minimal", "high"
            "max_output_tokens": None,
            "temperature": None,
            "max_retries": None,
        },
    ),
    "azure": ProviderCapabilities(
        supports_reasoning_effort=True,
        supports_max_output_tokens=True,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "reasoning_effort": None,
            "max_tokens": None,
            "temperature": None,
            "max_retries": None,
        },
    ),
    "bedrock": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "openrouter": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "deepseek": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "kimi": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "minimax": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "ollama": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "groq": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
    "mistral": ProviderCapabilities(
        supports_reasoning_effort=False,
        supports_max_output_tokens=False,
        supports_temperature=True,
        supports_max_retries=True,
        settings={
            "temperature": None,
            "max_retries": None,
        },
    ),
}


def get_capabilities(provider: str) -> ProviderCapabilities:
    """Return the capability profile for a provider, or a default one."""
    return PROVIDER_CAPABILITIES.get(provider.lower(), ProviderCapabilities())
