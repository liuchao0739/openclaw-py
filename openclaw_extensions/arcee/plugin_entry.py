from typing import Any, List, Optional, TypedDict

from .models import ARCEE_MODEL_CATALOG, build_arcee_model_definition
from .onboard import (
    ARCEE_DEFAULT_MODEL_REF,
    ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
    apply_arcee_config,
    apply_arcee_openrouter_config,
)
from .provider_catalog import (
    build_arcee_openrouter_provider,
    build_arcee_provider,
    normalize_arcee_openrouter_base_url,
    to_arcee_openrouter_model_id,
)

PROVIDER_ID = "arcee"

ARCEE_WIZARD_GROUP = {
    "groupId": "arcee",
    "groupLabel": "Arcee AI",
    "groupHint": "Direct API or OpenRouter",
}

OPENAI_COMPATIBLE_REPLAY_HOOKS: dict = {
    "replayModelRequest": None,
    "replayStreamChunk": None,
    "replayComplete": None,
}


def build_arcee_auth_methods() -> List[dict]:
    return [
        {
            "providerId": PROVIDER_ID,
            "methodId": "arcee-platform",
            "label": "Arcee AI API key",
            "hint": "Direct access to Arcee platform",
            "optionKey": "arceeaiApiKey",
            "flagName": "--arceeai-api-key",
            "envVar": "ARCEEAI_API_KEY",
            "promptMessage": "Enter Arcee AI API key",
            "defaultModel": ARCEE_DEFAULT_MODEL_REF,
            "expectedProviders": [PROVIDER_ID],
            "applyConfig": lambda cfg: apply_arcee_config(cfg),
            "wizard": {
                "choiceId": "arceeai-api-key",
                "choiceLabel": "Arcee AI API key",
                "choiceHint": "Direct (chat.arcee.ai)",
                **ARCEE_WIZARD_GROUP,
            },
        },
        {
            "providerId": PROVIDER_ID,
            "methodId": "openrouter",
            "label": "OpenRouter API key",
            "hint": "Access Arcee models via OpenRouter",
            "optionKey": "openrouterApiKey",
            "flagName": "--openrouter-api-key",
            "envVar": "OPENROUTER_API_KEY",
            "promptMessage": "Enter OpenRouter API key",
            "profileId": "openrouter:default",
            "defaultModel": ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
            "expectedProviders": [PROVIDER_ID, "openrouter"],
            "applyConfig": lambda cfg: apply_arcee_openrouter_config(cfg),
            "wizard": {
                "choiceId": "arceeai-openrouter",
                "choiceLabel": "OpenRouter API key",
                "choiceHint": "Via OpenRouter (openrouter.ai)",
                **ARCEE_WIZARD_GROUP,
            },
        },
    ]


def _resolve_api_key(ctx: dict, provider_id: str) -> Optional[str]:
    resolver = ctx.get("resolveProviderApiKey")
    if not callable(resolver):
        return None
    resolved = resolver(provider_id)
    if isinstance(resolved, dict):
        api_key = resolved.get("apiKey")
        if isinstance(api_key, str) and api_key:
            return api_key
        return None
    if isinstance(resolved, str) and resolved:
        return resolved
    return None


async def resolve_arcee_catalog(ctx: dict) -> Optional[dict]:
    direct_key = _resolve_api_key(ctx, PROVIDER_ID)
    if direct_key:
        provider = build_arcee_provider()
        provider["apiKey"] = direct_key
        return {"provider": provider}

    openrouter_key = _resolve_api_key(ctx, "openrouter")
    if openrouter_key:
        provider = build_arcee_openrouter_provider()
        provider["apiKey"] = openrouter_key
        return {"provider": provider}

    return None


def normalize_arcee_resolved_model(model: dict) -> Optional[dict]:
    normalized_base_url = normalize_arcee_openrouter_base_url(model.get("baseUrl"))
    if not normalized_base_url:
        return None
    model_id = model.get("id", "") if isinstance(model.get("id"), str) else ""
    normalized_id = to_arcee_openrouter_model_id(model_id)
    if normalized_id == model_id and normalized_base_url == model.get("baseUrl"):
        return None
    result = dict(model)
    result["id"] = normalized_id
    result["baseUrl"] = normalized_base_url
    return result


def _augment_model_catalog(params: dict) -> List[dict]:
    config = params.get("config", {})
    if not isinstance(config, dict):
        return []
    provider_id = params.get("providerId", PROVIDER_ID)
    providers = config.get("providers", {})
    if not isinstance(providers, dict):
        return []
    provider_cfg = providers.get(provider_id, {})
    if not isinstance(provider_cfg, dict):
        return []
    configured = provider_cfg.get("models", [])
    if isinstance(configured, list):
        return list(configured)
    return []


def _normalize_config(params: dict) -> Optional[dict]:
    provider_config = params.get("providerConfig", {})
    if not isinstance(provider_config, dict):
        return None
    base_url = provider_config.get("baseUrl")
    normalized_base_url = normalize_arcee_openrouter_base_url(base_url)
    if normalized_base_url and normalized_base_url != base_url:
        result = dict(provider_config)
        result["baseUrl"] = normalized_base_url
        return result
    return None


def _normalize_transport(params: dict) -> Optional[dict]:
    api = params.get("api")
    base_url = params.get("baseUrl")
    normalized_base_url = normalize_arcee_openrouter_base_url(base_url)
    if normalized_base_url and normalized_base_url != base_url:
        return {
            "api": api,
            "baseUrl": normalized_base_url,
        }
    return None


class PluginEntry(TypedDict, total=False):
    id: str
    name: str
    description: str
    provider: dict


plugin_entry: PluginEntry = {
    "id": PROVIDER_ID,
    "name": "Arcee AI Provider",
    "description": "Bundled Arcee AI provider plugin",
    "provider": {
        "label": "Arcee AI",
        "docsPath": "/providers/arcee",
        "envVars": ["ARCEEAI_API_KEY", "OPENROUTER_API_KEY"],
        "auth": build_arcee_auth_methods(),
        "catalog": {
            "run": resolve_arcee_catalog,
        },
        "augmentModelCatalog": _augment_model_catalog,
        "normalizeConfig": _normalize_config,
        "normalizeResolvedModel": lambda params: normalize_arcee_resolved_model(
            params.get("model", {}) if isinstance(params.get("model"), dict) else {}
        ),
        "normalizeTransport": _normalize_transport,
        **OPENAI_COMPATIBLE_REPLAY_HOOKS,
    },
}
