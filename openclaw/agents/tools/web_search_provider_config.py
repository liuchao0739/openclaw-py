"""Web search provider configuration.

Maps provider ids to display names, API key env vars, and endpoint URLs.
"""

from __future__ import annotations

from typing import Any, TypedDict


class WebSearchProviderConfig(TypedDict, total=False):
    id: str
    displayName: str
    apiKeyEnvVar: str
    endpoint: str
    maxResults: int


_WEB_SEARCH_PROVIDERS: dict[str, WebSearchProviderConfig] = {
    "brave": WebSearchProviderConfig(
        id="brave",
        displayName="Brave Search",
        apiKeyEnvVar="BRAVE_API_KEY",
        endpoint="https://api.search.brave.com/res/v1/web/search",
        maxResults=20,
    ),
    "duckduckgo": WebSearchProviderConfig(
        id="duckduckgo",
        displayName="DuckDuckGo",
        apiKeyEnvVar="",
        endpoint="https://html.duckduckgo.com/html/",
        maxResults=20,
    ),
    "exa": WebSearchProviderConfig(
        id="exa",
        displayName="Exa",
        apiKeyEnvVar="EXA_API_KEY",
        endpoint="https://api.exa.ai/search",
        maxResults=20,
    ),
    "google": WebSearchProviderConfig(
        id="google",
        displayName="Google Custom Search",
        apiKeyEnvVar="GOOGLE_API_KEY",
        endpoint="https://www.googleapis.com/customsearch/v1",
        maxResults=20,
    ),
}


def get_web_search_provider_config(provider: str | None) -> WebSearchProviderConfig | None:
    """Get the configuration for a web search provider."""
    if not provider:
        return None
    return _WEB_SEARCH_PROVIDERS.get(provider.lower())


def list_web_search_providers() -> list[str]:
    """List all registered web search provider ids."""
    return list(_WEB_SEARCH_PROVIDERS.keys())


def register_web_search_provider(provider_id: str, config: WebSearchProviderConfig) -> None:
    """Register or override a web search provider configuration."""
    _WEB_SEARCH_PROVIDERS[provider_id.lower()] = config


def resolve_web_search_api_key(
    provider: str | None,
    *,
    env: dict[str, str] | None = None,
) -> str | None:
    """Resolve the API key for a web search provider."""
    config = get_web_search_provider_config(provider)
    if not config:
        return None
    env_var = config.get("apiKeyEnvVar", "")
    if not env_var:
        return None
    import os

    env_map = env or os.environ
    value = env_map.get(env_var)
    if value and value.strip():
        return value.strip()
    return None
