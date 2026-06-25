"""Model config helpers for tool implementations.

Provides model resolution, provider lookup, and API key helpers
used by tools that interact with LLM providers.
"""

from __future__ import annotations

from typing import Any


def resolve_model_config(
    provider: str | None,
    model_id: str | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve model configuration from config and provider/model ids."""
    if not config or not provider:
        return None
    models = config.get("models")
    if not isinstance(models, dict):
        return None
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return None
    provider_config = providers.get(provider)
    if not isinstance(provider_config, dict):
        return None
    return provider_config


def get_api_key_env_var(provider: str | None) -> str | None:
    """Get the environment variable name for a provider's API key."""
    if not provider:
        return None
    mapping = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "together": "TOGETHER_API_KEY",
        "fireworks": "FIREWORKS_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
    }
    return mapping.get(provider.lower())


def resolve_api_key(
    provider: str | None,
    config: dict[str, Any] | None = None,
    *,
    env: dict[str, str] | None = None,
) -> str | None:
    """Resolve the API key for a provider from config or environment."""
    if not provider:
        return None
    provider_config = resolve_model_config(provider, None, config)
    if provider_config:
        api_key = provider_config.get("apiKey")
        if isinstance(api_key, str) and api_key.strip():
            return api_key.strip()

    env_var = get_api_key_env_var(provider)
    if env_var:
        import os

        env_map = env or os.environ
        value = env_map.get(env_var)
        if value and value.strip():
            return value.strip()
    return None
