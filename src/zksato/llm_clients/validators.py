from __future__ import annotations

# Known models per provider. Unknown models generate a warning but are still
# accepted (the provider may support them or may add them later).
KNOWN_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-6-sol",
        "gpt-6-luna",
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5",
        "gpt-4.5",
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


def validate_model(provider: str, model: str) -> bool:
    """Return True if the model is known for the provider.

    Unknown models return False (callers should warn but may still proceed).
    """
    known = KNOWN_MODELS.get(provider.lower(), [])
    if not known:
        # Provider not in catalog: accept any model
        return True
    return model in known


def suggest_models(provider: str) -> list[str]:
    """Return the list of known models for a provider."""
    return list(KNOWN_MODELS.get(provider.lower(), []))
