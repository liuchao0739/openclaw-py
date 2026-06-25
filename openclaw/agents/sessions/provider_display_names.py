"""Provider display name helpers.

Maps provider ids to human-readable display names for UI and diagnostics.
"""

from __future__ import annotations

_PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "groq": "Groq",
    "mistral": "Mistral AI",
    "cohere": "Cohere",
    "together": "Together AI",
    "fireworks": "Fireworks AI",
    "deepseek": "DeepSeek",
    "cerebras": "Cerebras",
    "perplexity": "Perplexity AI",
    "azure": "Azure OpenAI",
    "amazon-bedrock": "Amazon Bedrock",
    "ollama": "Ollama",
    "local": "Local",
}


def get_provider_display_name(provider: str | None) -> str:
    """Get the display name for a provider id."""
    if not provider:
        return "Unknown"
    return _PROVIDER_DISPLAY_NAMES.get(provider.lower(), provider)


def register_provider_display_name(provider: str, display_name: str) -> None:
    """Register or override a provider display name."""
    _PROVIDER_DISPLAY_NAMES[provider.lower()] = display_name
