"""Shared Brave Search provider metadata and credential lookup."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_web_search_contract import (
    create_web_search_provider_contract_fields,
)

BRAVE_CREDENTIAL_PATH = "plugins.entries.brave.config.webSearch.apiKey"


def resolve_legacy_top_level_brave_credential(
    config: Any,
) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    tools = config.get("tools")
    if not is_record(tools):
        return None
    web = tools.get("web")
    if not is_record(web):
        return None
    search = web.get("search")
    if not is_record(search) or "apiKey" not in search:
        return None
    return {"path": "tools.web.search.apiKey", "value": search["apiKey"]}


def _resolve_brave_web_search_plugin_config(config: Any) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    entry = entries.get("brave")
    if not is_record(entry):
        return None
    plugin_config = entry.get("config")
    if not is_record(plugin_config):
        return None
    web_search = plugin_config.get("webSearch")
    return dict(web_search) if is_record(web_search) else None


def resolve_configured_brave_credential(config: Any) -> Any:
    plugin_config = _resolve_brave_web_search_plugin_config(config)
    if plugin_config and "apiKey" in plugin_config:
        return plugin_config["apiKey"]
    legacy = resolve_legacy_top_level_brave_credential(config)
    return legacy["value"] if legacy else None


def build_brave_web_search_provider_base() -> dict[str, Any]:
    return {
        "id": "brave",
        "label": "Brave Search",
        "hint": "Structured results · country/language/time filters",
        "onboarding_scopes": ["text-inference"],
        "credential_label": "Brave Search API key",
        "env_vars": ["BRAVE_API_KEY"],
        "placeholder": "BSA...",
        "signup_url": "https://brave.com/search/api/",
        "docs_url": "https://docs.openclaw.ai/tools/brave-search",
        "auto_detect_order": 10,
        "credential_path": BRAVE_CREDENTIAL_PATH,
        **create_web_search_provider_contract_fields(
            {
                "credential_path": BRAVE_CREDENTIAL_PATH,
                "search_credential": {"type": "top-level"},
            }
        ),
        "get_configured_credential_value": resolve_configured_brave_credential,
        "get_configured_credential_fallback": resolve_legacy_top_level_brave_credential,
    }
