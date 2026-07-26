"""Groq plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.groq.media_understanding_provider import groq_media_understanding_provider

GROQ_DEFAULT_MODEL_REF = "groq/llama-3.3-70b-versatile"


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": "groq",
            "label": "Groq",
            "docsPath": "/providers/groq",
            "envVars": ["GROQ_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": "groq",
                        "methodId": "api-key",
                        "label": "Groq API key",
                        "hint": "Fast OpenAI-compatible inference",
                        "optionKey": "groqApiKey",
                        "flagName": "--groq-api-key",
                        "envVar": "GROQ_API_KEY",
                        "promptMessage": "Enter Groq API key",
                        "defaultModel": GROQ_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "groq-api-key",
                            "choiceLabel": "Groq API key",
                            "choiceHint": "Fast OpenAI-compatible inference",
                            "groupId": "groq",
                            "groupLabel": "Groq",
                            "groupHint": "Fast OpenAI-compatible inference",
                        },
                    }
                ),
            ],
        }
    )
    api.register_media_understanding_provider(groq_media_understanding_provider)


default = define_plugin_entry(
    id="groq",
    name="Groq Provider",
    description="Bundled Groq provider plugin",
    register=_register,
)
