from typing import Any, Optional


def _ensure_record(target: dict, key: str) -> dict:
    current = target.get(key)
    if isinstance(current, dict):
        return current
    next_record: dict = {}
    target[key] = next_record
    return next_record


FIRECRAWL_WEB_FETCH_PROVIDER_SHARED = {
    "id": "firecrawl",
    "label": "Firecrawl",
    "hint": "Fetch pages with keyless starter access; add a key for higher limits.",
    "requiresCredential": False,
    "credentialLabel": "Firecrawl API key (optional)",
    "envVars": ["FIRECRAWL_API_KEY"],
    "placeholder": "fc-...",
    "signupUrl": "https://www.firecrawl.dev/",
    "docsUrl": "https://docs.firecrawl.dev",
    "autoDetectOrder": 50,
    "credentialPath": "plugins.entries.firecrawl.config.webFetch.apiKey",
    "inactiveSecretPaths": [
        "plugins.entries.firecrawl.config.webFetch.apiKey",
        "tools.web.fetch.firecrawl.apiKey",
    ],
    "getCredentialValue": lambda fetch_config: (
        None
        if not isinstance(fetch_config, dict)
        else (
            None
            if not isinstance(fetch_config.get("firecrawl"), dict)
            or fetch_config["firecrawl"].get("enabled") is False
            else fetch_config["firecrawl"].get("apiKey")
        )
    ),
    "setCredentialValue": lambda fetch_config_target, value: _ensure_record(
        fetch_config_target, "firecrawl"
    ).__setitem__("apiKey", value),
    "getConfiguredCredentialValue": lambda config: (
        config.get("plugins", {})
        .get("entries", {})
        .get("firecrawl", {})
        .get("config", {})
        .get("webFetch", {})
        .get("apiKey")
        if config
        else None
    ),
    "getConfiguredCredentialFallback": lambda config: (
        None
        if not config
        else (
            None
            if (config.get("plugins", {}).get("entries", {}).get("firecrawl", {}).get("config", {}).get("webSearch", {}).get("apiKey") is None)
            else {
                "path": "plugins.entries.firecrawl.config.webSearch.apiKey",
                "value": config.get("plugins", {})
                .get("entries", {})
                .get("firecrawl", {})
                .get("config", {})
                .get("webSearch", {})
                .get("apiKey"),
            }
        )
    ),
    "setConfiguredCredentialValue": lambda config_target, value: _ensure_record(
        _ensure_record(
            _ensure_record(
                _ensure_record(_ensure_record(config_target, "plugins"), "entries"),
                "firecrawl",
            ),
            "config",
        ),
        "webFetch",
    ).__setitem__("apiKey", value),
}
