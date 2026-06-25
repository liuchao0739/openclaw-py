"""Provider API family constants.

Maps provider ids to their supported API families (chat completions, responses, etc.).
"""

from __future__ import annotations

from typing import Literal

ApiFamily = Literal["openai-chat", "openai-responses", "anthropic-messages", "google-gemini", "generic"]

_PROVIDER_API_FAMILIES: dict[str, ApiFamily] = {
    "openai": "openai-responses",
    "openai-codex": "openai-responses",
    "anthropic": "anthropic-messages",
    "google": "google-gemini",
    "azure": "openai-chat",
    "together": "openai-chat",
    "fireworks": "openai-chat",
    "groq": "openai-chat",
    "mistral": "openai-chat",
    "cohere": "openai-chat",
    "deepseek": "openai-chat",
    "perplexity": "openai-chat",
}


def get_provider_api_family(provider: str | None) -> ApiFamily:
    """Get the API family for a provider."""
    if not provider:
        return "generic"
    return _PROVIDER_API_FAMILIES.get(provider.lower(), "generic")


def register_provider_api_family(provider: str, family: ApiFamily) -> None:
    """Register or override the API family for a provider."""
    _PROVIDER_API_FAMILIES[provider.lower()] = family
