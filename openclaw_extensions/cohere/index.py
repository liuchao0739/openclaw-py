"""Cohere plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.cohere.onboard import COHERE_DEFAULT_MODEL_REF, apply_cohere_config
from openclaw_extensions.cohere.provider_catalog import build_cohere_provider
from openclaw_extensions.cohere.stream import create_cohere_completions_wrapper


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": "cohere",
            "label": "Cohere",
            "docsPath": "/providers/cohere",
            "envVars": ["COHERE_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": "cohere",
                        "methodId": "api-key",
                        "label": "Cohere API key",
                        "hint": "OpenAI-compatible inference",
                        "optionKey": "cohereApiKey",
                        "flagName": "--cohere-api-key",
                        "envVar": "COHERE_API_KEY",
                        "promptMessage": "Enter Cohere API key",
                        "defaultModel": COHERE_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "cohere-api-key",
                            "choiceLabel": "Cohere API key",
                            "choiceHint": "OpenAI-compatible inference",
                            "groupId": "cohere",
                            "groupLabel": "Cohere",
                            "groupHint": "OpenAI-compatible inference",
                        },
                    }
                ),
            ],
            "catalog": {
                "buildProvider": build_cohere_provider,
                "buildStaticProvider": build_cohere_provider,
            },
            "wrapStreamFn": lambda ctx: create_cohere_completions_wrapper(ctx.get("streamFn")),
            "wrapSimpleCompletionStreamFn": lambda ctx: create_cohere_completions_wrapper(
                ctx.get("streamFn")
            ),
            "applyConfig": apply_cohere_config,
        }
    )


default = define_plugin_entry(
    id="cohere",
    name="Cohere Provider",
    description="Cohere provider plugin",
    register=_register,
)
