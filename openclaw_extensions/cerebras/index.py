"""Cerebras provider plugin entrypoint."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.cerebras.onboard import CEREBRAS_DEFAULT_MODEL_REF, apply_cerebras_config
from openclaw_extensions.cerebras.provider_catalog import build_cerebras_provider


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": "cerebras",
            "label": "Cerebras",
            "docsPath": "/providers/cerebras",
            "envVars": ["CEREBRAS_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": "cerebras",
                        "methodId": "api-key",
                        "label": "Cerebras API key",
                        "hint": "Fast OpenAI-compatible inference",
                        "optionKey": "cerebrasApiKey",
                        "flagName": "--cerebras-api-key",
                        "envVar": "CEREBRAS_API_KEY",
                        "promptMessage": "Enter Cerebras API key",
                        "defaultModel": CEREBRAS_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "cerebras-api-key",
                            "choiceLabel": "Cerebras API key",
                            "choiceHint": "Fast OpenAI-compatible inference",
                            "groupId": "cerebras",
                            "groupLabel": "Cerebras",
                            "groupHint": "Fast OpenAI-compatible inference",
                        },
                    }
                ),
            ],
            "catalog": {
                "buildProvider": build_cerebras_provider,
                "buildStaticProvider": build_cerebras_provider,
            },
            "applyConfig": apply_cerebras_config,
        }
    )


default = define_plugin_entry(
    id="cerebras",
    name="Cerebras Provider",
    description="Bundled Cerebras provider plugin",
    register=_register,
)
