"""BytePlus provider plugin entrypoint for model and video generation providers."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.byteplus.models import (
    BYTEPLUS_CODING_MODEL_CATALOG,
    BYTEPLUS_MODEL_CATALOG,
)
from openclaw_extensions.byteplus.provider_catalog import (
    build_byte_plus_coding_provider,
    build_byte_plus_provider,
)
from openclaw_extensions.byteplus.video_generation_provider import (
    build_byte_plus_video_generation_provider,
)

PROVIDER_ID = "byteplus"
BYTEPLUS_DEFAULT_MODEL_REF = "byteplus-plan/ark-code-latest"


def _augment_byteplus_model_catalog(_ctx: dict[str, Any]) -> list[dict[str, Any]]:
    byteplus_models = [
        {
            "provider": "byteplus",
            "id": entry["id"],
            "name": entry["name"],
            "reasoning": entry.get("reasoning"),
            "input": list(entry["input"]),
            "contextWindow": entry["contextWindow"],
        }
        for entry in BYTEPLUS_MODEL_CATALOG
    ]
    byteplus_plan_models = [
        {
            "provider": "byteplus-plan",
            "id": entry["id"],
            "name": entry["name"],
            "reasoning": entry.get("reasoning"),
            "input": list(entry["input"]),
            "contextWindow": entry["contextWindow"],
        }
        for entry in BYTEPLUS_CODING_MODEL_CATALOG
    ]
    return [*byteplus_models, *byteplus_plan_models]


async def _byteplus_catalog_run(ctx: dict[str, Any]) -> dict[str, Any] | None:
    resolve_provider_api_key = ctx["resolveProviderApiKey"]
    api_key = resolve_provider_api_key(PROVIDER_ID).get("apiKey")
    if not api_key:
        return None
    return {
        "providers": {
            "byteplus": {**build_byte_plus_provider(), "apiKey": api_key},
            "byteplus-plan": {**build_byte_plus_coding_provider(), "apiKey": api_key},
        }
    }


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "BytePlus",
            "docsPath": "/concepts/model-providers#byteplus-international",
            "envVars": ["BYTEPLUS_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "BytePlus API key",
                        "hint": "API key",
                        "optionKey": "byteplusApiKey",
                        "flagName": "--byteplus-api-key",
                        "envVar": "BYTEPLUS_API_KEY",
                        "promptMessage": "Enter BytePlus API key",
                        "defaultModel": BYTEPLUS_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "byteplus-api-key",
                            "choiceLabel": "BytePlus API key",
                            "groupId": "byteplus",
                            "groupLabel": "BytePlus",
                            "groupHint": "API key",
                        },
                    }
                ),
            ],
            "catalog": {
                "order": "paired",
                "run": _byteplus_catalog_run,
            },
            "augmentModelCatalog": _augment_byteplus_model_catalog,
        }
    )
    api.register_video_generation_provider(build_byte_plus_video_generation_provider())


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="BytePlus Provider",
    description="Bundled BytePlus provider plugin",
    register=_register,
)
