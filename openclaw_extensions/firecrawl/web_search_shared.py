from typing import Optional

from .._sdk import create_web_search_provider_contract_fields, enable_plugin_in_config

FIRECRAWL_CREDENTIAL_PATH = "plugins.entries.firecrawl.config.webSearch.apiKey"
FIRECRAWL_FETCH_CREDENTIAL_PATH = "plugins.entries.firecrawl.config.webFetch.apiKey"


def get_configured_firecrawl_fetch_credential_fallback(config: dict) -> Optional[dict]:
    if not config:
        return None
    api_key = (
        config.get("plugins", {})
        .get("entries", {})
        .get("firecrawl", {})
        .get("config", {})
        .get("webFetch", {})
        .get("apiKey")
    )
    if api_key is None:
        return None
    return {"path": FIRECRAWL_FETCH_CREDENTIAL_PATH, "value": api_key}


def build_firecrawl_web_search_provider_base() -> dict:
    contract_fields = create_web_search_provider_contract_fields(
        credential_path=FIRECRAWL_CREDENTIAL_PATH,
        search_credential={"type": "scoped", "scopeId": "firecrawl"},
        configured_credential={"pluginId": "firecrawl"},
    )

    def apply_selection_config(config: dict) -> dict:
        enabled_config = enable_plugin_in_config(config, "firecrawl")
        tools_web = enabled_config.get("tools", {}).get("web", {})
        if tools_web.get("fetch", {}).get("provider"):
            return enabled_config
        enabled_config.setdefault("tools", {}).setdefault("web", {}).setdefault("fetch", {})["provider"] = "firecrawl"
        return enabled_config

    base = {
        "id": "firecrawl",
        "label": "Firecrawl Search",
        "hint": "Structured results with optional result scraping",
        "onboardingScopes": ["text-inference"],
        "credentialLabel": "Firecrawl API key",
        "envVars": ["FIRECRAWL_API_KEY"],
        "placeholder": "fc-...",
        "signupUrl": "https://www.firecrawl.dev/",
        "docsUrl": "https://docs.openclaw.ai/tools/firecrawl",
        "autoDetectOrder": 60,
        "credentialPath": FIRECRAWL_CREDENTIAL_PATH,
    }
    base.update(contract_fields)
    base["applySelectionConfig"] = apply_selection_config
    base["getConfiguredCredentialFallback"] = get_configured_firecrawl_fetch_credential_fallback
    return base
