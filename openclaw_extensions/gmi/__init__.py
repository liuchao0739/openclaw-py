"""GMI Cloud provider extension."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.gmi.models import GMI_DEFAULT_MODEL_REF
from openclaw_extensions.gmi.provider_catalog import build_gmi_provider

PROVIDER_ID = "gmi"


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "GMI Cloud",
            "docsPath": "/providers/gmi",
            "aliases": ["gmi-cloud", "gmicloud"],
            "envVars": ["GMI_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "GMI Cloud API key",
                        "hint": "OpenAI-compatible GMI Cloud endpoint",
                        "optionKey": "gmiApiKey",
                        "flagName": "--gmi-api-key",
                        "envVar": "GMI_API_KEY",
                        "promptMessage": "Enter GMI Cloud API key",
                        "defaultModel": GMI_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "gmi-api-key",
                            "choiceLabel": "GMI Cloud API key",
                            "choiceHint": "OpenAI-compatible GMI Cloud endpoint",
                            "groupId": "gmi",
                            "groupLabel": "GMI Cloud",
                            "groupHint": "OpenAI-compatible GMI Cloud endpoint",
                        },
                    }
                ),
            ],
            "catalog": {
                "buildProvider": build_gmi_provider,
                "buildStaticProvider": build_gmi_provider,
                "allowExplicitBaseUrl": True,
            },
            "replayFamily": "openai-compatible",
            "dropReasoningFromHistory": False,
            "toolCompatFamily": "openai",
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="GMI Cloud Provider",
    description="GMI Cloud provider plugin",
    register=_register,
)