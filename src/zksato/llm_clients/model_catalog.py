from __future__ import annotations


class ModelCatalog:
    """Catalog of known models per provider with metadata.

    Provides model discovery, categorization, and tier recommendations
    (quick vs deep thinking models).
    """

    def __init__(self, providers: dict[str, list[str]] | None = None) -> None:
        self._models: dict[str, list[str]] = dict(providers or {})

    def register_provider(self, provider: str, models: list[str]) -> None:
        self._models[provider.lower()] = list(models)

    def list_providers(self) -> list[str]:
        return sorted(self._models.keys())

    def list_models(self, provider: str) -> list[str]:
        return list(self._models.get(provider.lower(), []))

    def has_model(self, provider: str, model: str) -> bool:
        return model in self._models.get(provider.lower(), [])

    def suggest_quick_think(self, provider: str) -> str | None:
        """Suggest a quick-thinking (lower latency) model for a provider."""
        models = self.list_models(provider)
        # Prefer smaller/faster models first
        preferences = ["mini", "flash", "haiku", "luna", "small", "8b", "7b"]
        for pref in preferences:
            for m in models:
                if pref.lower() in m.lower():
                    return m
        return models[0] if models else None

    def suggest_deep_think(self, provider: str) -> str | None:
        """Suggest a deep-thinking (higher capability) model for a provider."""
        models = self.list_models(provider)
        # Prefer larger/more capable models first
        preferences = ["sol", "sonnet", "pro", "opus", "luna", "large", "70b", "turbo"]
        for pref in preferences:
            for m in models:
                if pref.lower() in m.lower():
                    return m
        return models[-1] if models else None

    def get_all(self) -> dict[str, list[str]]:
        return dict(self._models)


# Default catalog seeded with known models
DEFAULT_CATALOG = ModelCatalog(
    {
        "openai": [
            "gpt-6-sol",
            "gpt-6-luna",
            "gpt-5.5",
            "gpt-5",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "anthropic": [
            "claude-4.6",
            "claude-4.5",
            "claude-4",
            "claude-3.7-sonnet",
            "claude-3.5-sonnet",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
        ],
        "google": [
            "gemini-3.1",
            "gemini-3",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "azure": [
            "gpt-6-sol",
            "gpt-6-luna",
            "gpt-5.5",
            "gpt-5",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "bedrock": [
            "anthropic.claude-4-sonnet",
            "anthropic.claude-3-sonnet",
            "anthropic.claude-3-haiku",
            "amazon.titan-text-express",
            "amazon.titan-text-lite",
            "meta.llama3-8b",
            "meta.llama3-70b",
            "cohere.command-r-plus",
            "cohere.command-r",
            "ai21.j2-mid",
            "ai21.j2-ultra",
        ],
        "openrouter": [
            "openrouter/auto",
            "openrouter/gpt-6-sol",
            "openrouter/claude-4.6",
            "openrouter/gemini-3.1",
        ],
        "deepseek": [
            "deepseek-v4-flash",
            "deepseek-v3",
            "deepseek-chat",
            "deepseek-coder",
        ],
        "kimi": [
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
        ],
        "minimax": [
            "minimax-01",
            "abab6.5-chat",
            "abab5.5-chat",
        ],
        "ollama": [
            "llama3.1",
            "llama3.2",
            "llama3.3",
            "qwen2.5",
            "gemma2",
            "mistral-nemo",
        ],
        "groq": [
            "llama-3.1-8b",
            "llama-3.1-70b",
            "llama-3.3-70b",
            "mixtral-8x7b",
            "gemma2-9b",
        ],
        "mistral": [
            "mistral-large",
            "mistral-medium",
            "mistral-small",
            "codestral",
        ],
        "cohere": [
            "command-r-plus",
            "command-r",
            "command",
        ],
        "huggingface": [
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-70B",
            "mistralai/Mistral-7B-Instruct",
        ],
        "together": [
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-70B",
            "mistralai/Mixtral-8x7B",
        ],
        "perplexity": [
            "llama-3.1-sonar-small-128k",
            "llama-3.1-sonar-large-128k",
            "llama-3.1-sonar-huge-128k",
        ],
    }
)
