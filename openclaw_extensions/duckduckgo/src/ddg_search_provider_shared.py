"""DuckDuckGo provider module implements model/runtime integration."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_web_search_contract import (
    create_web_search_provider_contract_fields,
)

_DUCKDUCKGO_ONBOARDING_SCOPES = ["text-inference"]


def create_duck_duck_go_web_search_provider_base() -> dict:
    return {
        "id": "duckduckgo",
        "label": "DuckDuckGo Search (experimental)",
        "hint": "Free web search fallback with no API key required",
        "onboarding_scopes": list(_DUCKDUCKGO_ONBOARDING_SCOPES),
        "requires_credential": False,
        "env_vars": [],
        "placeholder": "(no key needed)",
        "signup_url": "https://duckduckgo.com/",
        "docs_url": "https://docs.openclaw.ai/tools/web",
        "auto_detect_order": 100,
        "credential_path": "",
        **create_web_search_provider_contract_fields(
            {
                "credential_path": "",
                "search_credential": {"type": "scoped", "scopeId": "duckduckgo"},
                "selection_plugin_id": "duckduckgo",
            }
        ),
    }
