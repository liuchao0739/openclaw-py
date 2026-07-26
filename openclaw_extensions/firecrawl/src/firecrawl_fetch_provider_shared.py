"""Firecrawl provider module implements model/runtime integration."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record


def _ensure_record(target: dict[str, Any], key: str) -> dict[str, Any]:
    current = target.get(key)
    if is_record(current) and not isinstance(current, list):
        return current
    next_value: dict[str, Any] = {}
    target[key] = next_value
    return next_value


def _get_credential_value(fetch_config: Any) -> Any:
    if not is_record(fetch_config):
        return None
    legacy = fetch_config.get("firecrawl")
    if not is_record(legacy) or isinstance(legacy, list):
        return None
    if legacy.get("enabled") is False:
        return None
    return legacy.get("apiKey")


def _set_credential_value(fetch_config_target: dict[str, Any], value: Any) -> None:
    firecrawl = _ensure_record(fetch_config_target, "firecrawl")
    firecrawl["apiKey"] = value


def _get_configured_credential_value(config: Any) -> Any:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    firecrawl_entry = entries.get("firecrawl")
    if not is_record(firecrawl_entry):
        return None
    plugin_config = firecrawl_entry.get("config")
    if not is_record(plugin_config):
        return None
    web_fetch = plugin_config.get("webFetch")
    if not is_record(web_fetch):
        return None
    return web_fetch.get("apiKey")


def _get_configured_credential_fallback(config: Any) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    firecrawl_entry = entries.get("firecrawl")
    if not is_record(firecrawl_entry):
        return None
    plugin_config = firecrawl_entry.get("config")
    if not is_record(plugin_config):
        return None
    web_search = plugin_config.get("webSearch")
    if not is_record(web_search):
        return None
    api_key = web_search.get("apiKey")
    if api_key is None:
        return None
    return {
        "path": "plugins.entries.firecrawl.config.webSearch.apiKey",
        "value": api_key,
    }


def _set_configured_credential_value(config_target: dict[str, Any], value: Any) -> None:
    plugins = _ensure_record(config_target, "plugins")
    entries = _ensure_record(plugins, "entries")
    firecrawl_entry = _ensure_record(entries, "firecrawl")
    plugin_config = _ensure_record(firecrawl_entry, "config")
    web_fetch = _ensure_record(plugin_config, "webFetch")
    web_fetch["apiKey"] = value


FIRECRAWL_WEB_FETCH_PROVIDER_SHARED = {
    "id": "firecrawl",
    "label": "Firecrawl",
    "hint": "Fetch pages with keyless starter access; add a key for higher limits.",
    "requires_credential": False,
    "credential_label": "Firecrawl API key (optional)",
    "env_vars": ["FIRECRAWL_API_KEY"],
    "placeholder": "fc-...",
    "signup_url": "https://www.firecrawl.dev/",
    "docs_url": "https://docs.firecrawl.dev",
    "auto_detect_order": 50,
    "credential_path": "plugins.entries.firecrawl.config.webFetch.apiKey",
    "inactive_secret_paths": [
        "plugins.entries.firecrawl.config.webFetch.apiKey",
        "tools.web.fetch.firecrawl.apiKey",
    ],
    "get_credential_value": _get_credential_value,
    "set_credential_value": _set_credential_value,
    "get_configured_credential_value": _get_configured_credential_value,
    "get_configured_credential_fallback": _get_configured_credential_fallback,
    "set_configured_credential_value": _set_configured_credential_value,
}
