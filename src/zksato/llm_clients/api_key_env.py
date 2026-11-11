from __future__ import annotations

import os

# Environment variable names per provider. The first match wins.
API_KEY_ENV_VARS: dict[str, list[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "azure": ["AZURE_OPENAI_API_KEY", "AZURE_API_KEY"],
    "bedrock": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
    "bedrock_runtime": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
    "openrouter": ["OPENROUTER_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "kimi": ["MOONSHOT_API_KEY"],
    "minimax": ["MINIMAX_API_KEY"],
    "ollama": [],  # Ollama typically does not require an API key
    "groq": ["GROQ_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "huggingface": ["HF_API_KEY", "HUGGINGFACE_API_KEY"],
    "together": ["TOGETHER_API_KEY"],
    "perplexity": ["PERPLEXITY_API_KEY"],
}


def detect_api_key_env(provider: str) -> str | None:
    """Return the first present API key env var for a provider, or None."""
    for var in API_KEY_ENV_VARS.get(provider.lower(), []):
        value = os.environ.get(var)
        if value and value.strip():
            return var
    return None


def get_api_key(provider: str) -> str | None:
    """Return the API key value for a provider, or None if not configured."""
    env_var = detect_api_key_env(provider)
    if env_var is None:
        return None
    return os.environ.get(env_var, "").strip() or None


def require_api_key(provider: str) -> str:
    """Return the API key for a provider, raising if not configured."""
    key = get_api_key(provider)
    if not key:
        env_vars = ", ".join(API_KEY_ENV_VARS.get(provider.lower(), [])) or "<none documented>"
        raise ValueError(f"No API key configured for provider '{provider}'. Set one of: {env_vars}")
    return key


def mask_api_key(key: str | None) -> str:
    """Mask an API key for safe logging/display."""
    if not key:
        return "<unset>"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
