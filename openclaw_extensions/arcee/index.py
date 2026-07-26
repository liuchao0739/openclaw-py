"""Arcee AI provider plugin entry supporting direct API and OpenRouter routing."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.arcee.onboard import (
    ARCEE_DEFAULT_MODEL_REF,
    ARCEE_OPENROUTER_DEFAULT_MODEL_REF,
)
from openclaw_extensions.arcee.provider_catalog import (
    build_arcee_open_router_provider,
    build_arcee_provider,
    normalize_arcee_open_router_base_url,
    to_arcee_open_router_model_id,
)

PROVIDER_ID = "arcee"
_ARCEE_WIZARD_GROUP = {
    "groupId": "arcee",
    "groupLabel": "Arcee AI",
    "groupHint": "Direct API or OpenRouter",
}


def _build_arcee_auth_methods() -> list[dict[str, Any]]:
    return [
        create_provider_api_key_auth_method(
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
                "wizard": {
                    "choiceId": "arceeai-api-key",
                    "choiceLabel": "Arcee AI API key",
                    "choiceHint": "Direct (chat.arcee.ai)",
                    **_ARCEE_WIZARD_GROUP,
                },
            }
        ),
        create_provider_api_key_auth_method(
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
                "wizard": {
                    "choiceId": "arceeai-openrouter",
                    "choiceLabel": "OpenRouter API key",
                    "choiceHint": "Via OpenRouter (openrouter.ai)",
                    **_ARCEE_WIZARD_GROUP,
                },
            }
        ),
    ]


async def resolve_arcee_catalog(ctx: dict[str, Any]) -> dict[str, Any] | None:
    resolve_provider_api_key = ctx["resolveProviderApiKey"]
    direct_key = resolve_provider_api_key(PROVIDER_ID).get("apiKey")
    if direct_key:
        return {"provider": {**build_arcee_provider(), "apiKey": direct_key}}

    open_router_key = resolve_provider_api_key("openrouter").get("apiKey")
    if open_router_key:
        return {"provider": {**build_arcee_open_router_provider(), "apiKey": open_router_key}}

    return None


def normalize_arcee_resolved_model(model: dict[str, Any]) -> dict[str, Any] | None:
    normalized_base_url = normalize_arcee_open_router_base_url(model.get("baseUrl"))
    if not normalized_base_url:
        return None
    normalized_id = to_arcee_open_router_model_id(model["id"])
    if normalized_id == model["id"] and normalized_base_url == model.get("baseUrl"):
        return None
    return {
        **model,
        "id": normalized_id,
        "baseUrl": normalized_base_url,
    }


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Arcee AI",
            "docsPath": "/providers/arcee",
            "envVars": ["ARCEEAI_API_KEY", "OPENROUTER_API_KEY"],
            "auth": _build_arcee_auth_methods(),
            "catalog": {
                "run": resolve_arcee_catalog,
            },
            "normalizeConfig": lambda ctx: _normalize_provider_config(ctx.get("providerConfig", {})),
            "normalizeResolvedModel": lambda ctx: normalize_arcee_resolved_model(
                ctx.get("model", {})
            ),
            "normalizeTransport": lambda ctx: _normalize_transport(ctx),
        }
    )


def _normalize_provider_config(provider_config: dict[str, Any]) -> dict[str, Any] | None:
    normalized_base_url = normalize_arcee_open_router_base_url(provider_config.get("baseUrl"))
    if normalized_base_url and normalized_base_url != provider_config.get("baseUrl"):
        return {**provider_config, "baseUrl": normalized_base_url}
    return None


def _normalize_transport(ctx: dict[str, Any]) -> dict[str, Any] | None:
    normalized_base_url = normalize_arcee_open_router_base_url(ctx.get("baseUrl"))
    if normalized_base_url and normalized_base_url != ctx.get("baseUrl"):
        return {
            "api": ctx.get("api"),
            "baseUrl": normalized_base_url,
        }
    return None


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Arcee AI Provider",
    description="Bundled Arcee AI provider plugin",
    register=_register,
)
