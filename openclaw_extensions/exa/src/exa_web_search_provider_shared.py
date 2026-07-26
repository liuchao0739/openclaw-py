"""Exa provider module implements model/runtime integration."""

from __future__ import annotations

from openclaw.plugin_sdk.provider_web_search_contract import (
    create_web_search_provider_contract_fields,
)

EXA_CREDENTIAL_PATH = "plugins.entries.exa.config.webSearch.apiKey"
EXA_ONBOARDING_SCOPES = ["text-inference"]


def create_exa_web_search_provider_base() -> dict:
    return {
        "id": "exa",
        "label": "Exa Search",
        "hint": "Neural + keyword search with date filters and content extraction",
        "onboarding_scopes": list(EXA_ONBOARDING_SCOPES),
        "credential_label": "Exa API key",
        "env_vars": ["EXA_API_KEY"],
        "placeholder": "exa-...",
        "signup_url": "https://exa.ai/",
        "docs_url": "https://docs.openclaw.ai/tools/web",
        "auto_detect_order": 65,
        "credential_path": EXA_CREDENTIAL_PATH,
        **create_web_search_provider_contract_fields(
            {
                "credential_path": EXA_CREDENTIAL_PATH,
                "search_credential": {"type": "scoped", "scopeId": "exa"},
                "configured_credential": {"pluginId": "exa"},
                "selection_plugin_id": "exa",
            }
        ),
    }
