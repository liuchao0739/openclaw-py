"""Brave Search test API barrel for normalization helpers."""

from openclaw_extensions.brave.src.brave_web_search_provider_shared import (
    map_brave_llm_context_results,
    normalize_brave_country,
    normalize_brave_language_params,
    resolve_brave_mode,
)

testing = {
    "normalize_brave_country": normalize_brave_country,
    "normalize_brave_language_params": normalize_brave_language_params,
    "resolve_brave_mode": resolve_brave_mode,
    "map_brave_llm_context_results": map_brave_llm_context_results,
}

__testing = testing

__all__ = ["__testing", "testing"]
