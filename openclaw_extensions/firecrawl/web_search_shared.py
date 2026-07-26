"""Firecrawl plugin module implements web search shared behavior."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.provider_enable_config import enable_plugin_in_config
from openclaw.plugin_sdk.provider_web_search import resolve_provider_web_search_plugin_config
from openclaw.plugin_sdk.provider_web_search_contract import (
    create_web_search_provider_contract_fields,
)

FIRECRAWL_CREDENTIAL_PATH = "plugins.entries.firecrawl.config.webSearch.apiKey"
FIRECRAWL_FETCH_CREDENTIAL_PATH = "plugins.entries.firecrawl.config.webFetch.apiKey"


def get_configured_firecrawl_fetch_credential_fallback(
    config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
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
    api_key = web_fetch.get("apiKey")
    if api_key is None:
        return None
    return {"path": FIRECRAWL_FETCH_CREDENTIAL_PATH, "value": api_key}


def build_firecrawl_web_search_provider_base() -> dict[str, Any]:
    contract_fields = create_web_search_provider_contract_fields(
        {
            "credential_path": FIRECRAWL_CREDENTIAL_PATH,
            "search_credential": {"type": "scoped", "scopeId": "firecrawl"},
            "configured_credential": {"pluginId": "firecrawl"},
        }
    )

    def get_configured_credential_value(config: dict[str, Any] | None = None) -> Any:
        plugin_config = resolve_provider_web_search_plugin_config(config, "firecrawl")
        return plugin_config.get("apiKey") if plugin_config else None

    def apply_selection_config(config: dict[str, Any]) -> dict[str, Any]:
        enabled = enable_plugin_in_config(config, "firecrawl")
        if not enabled["enabled"]:
            return enabled["config"]
        next_config = enabled["config"]
        tools = next_config.get("tools")
        if is_record(tools):
            web = tools.get("web")
            if is_record(web):
                fetch = web.get("fetch")
                if is_record(fetch) and fetch.get("provider"):
                    return next_config
        next_config = deepcopy(next_config)
        next_tools = dict(next_config.get("tools") or {})
        next_web = dict(next_tools.get("web") or {})
        next_fetch = dict(next_web.get("fetch") or {})
        next_fetch["provider"] = "firecrawl"
        next_web["fetch"] = next_fetch
        next_tools["web"] = next_web
        next_config["tools"] = next_tools
        return next_config

    return {
        "id": "firecrawl",
        "label": "Firecrawl Search",
        "hint": "Structured results with optional result scraping",
        "onboarding_scopes": ["text-inference"],
        "credential_label": "Firecrawl API key",
        "env_vars": ["FIRECRAWL_API_KEY"],
        "placeholder": "fc-...",
        "signup_url": "https://www.firecrawl.dev/",
        "docs_url": "https://docs.openclaw.ai/tools/firecrawl",
        "auto_detect_order": 60,
        "credential_path": FIRECRAWL_CREDENTIAL_PATH,
        **contract_fields,
        "apply_selection_config": apply_selection_config,
        "get_configured_credential_value": get_configured_credential_value,
        "get_configured_credential_fallback": get_configured_firecrawl_fetch_credential_fallback,
    }
