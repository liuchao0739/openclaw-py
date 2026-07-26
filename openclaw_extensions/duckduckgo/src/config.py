"""DuckDuckGo helper module supports config behavior."""

from __future__ import annotations

from typing import Any, Literal

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

DEFAULT_DDG_SAFE_SEARCH = "moderate"

DdgSafeSearch = Literal["strict", "moderate", "off"]


def _resolve_ddg_web_search_config(config: dict[str, Any] | None) -> dict[str, Any] | None:
    if not config:
        return None
    plugins = config.get("plugins")
    if not isinstance(plugins, dict):
        return None
    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        return None
    plugin_config = entries.get("duckduckgo")
    if not isinstance(plugin_config, dict):
        return None
    config_body = plugin_config.get("config")
    if not isinstance(config_body, dict):
        return None
    web_search = config_body.get("webSearch")
    if isinstance(web_search, dict) and not isinstance(web_search, list):
        return web_search
    return None


def resolve_ddg_region(config: dict[str, Any] | None = None) -> str | None:
    region = _resolve_ddg_web_search_config(config)
    if not region:
        return None
    raw_region = region.get("region")
    if not isinstance(raw_region, str):
        return None
    trimmed = raw_region.strip()
    return trimmed or None


def resolve_ddg_safe_search(config: dict[str, Any] | None = None) -> DdgSafeSearch:
    web_search = _resolve_ddg_web_search_config(config)
    safe_search = web_search.get("safeSearch") if web_search else None
    normalized = normalize_lowercase_string_or_empty(safe_search)
    if normalized in ("strict", "off"):
        return normalized  # type: ignore[return-value]
    return DEFAULT_DDG_SAFE_SEARCH
