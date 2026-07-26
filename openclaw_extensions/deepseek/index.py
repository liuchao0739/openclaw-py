"""DeepSeek plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

import re

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.deepseek.onboard import DEEPSEEK_DEFAULT_MODEL_REF, apply_deep_seek_config
from openclaw_extensions.deepseek.provider_catalog import build_deep_seek_provider
from openclaw_extensions.deepseek.stream import create_deep_seek_v4_thinking_wrapper
from openclaw_extensions.deepseek.thinking import resolve_deep_seek_v4_thinking_profile

PROVIDER_ID = "deepseek"
_CONTEXT_OVERFLOW_PATTERN = re.compile(r"\bdeepseek\b.*(?:input.*too long|context.*exceed)", re.IGNORECASE)


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "DeepSeek",
            "docsPath": "/providers/deepseek",
            "envVars": ["DEEPSEEK_API_KEY"],
            "auth": [
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "DeepSeek API key",
                        "hint": "API key",
                        "optionKey": "deepseekApiKey",
                        "flagName": "--deepseek-api-key",
                        "envVar": "DEEPSEEK_API_KEY",
                        "promptMessage": "Enter DeepSeek API key",
                        "defaultModel": DEEPSEEK_DEFAULT_MODEL_REF,
                        "wizard": {
                            "choiceId": "deepseek-api-key",
                            "choiceLabel": "DeepSeek API key",
                            "groupId": "deepseek",
                            "groupLabel": "DeepSeek",
                            "groupHint": "API key",
                        },
                    }
                ),
            ],
            "catalog": {
                "buildProvider": build_deep_seek_provider,
            },
            "matchesContextOverflowError": lambda ctx: _CONTEXT_OVERFLOW_PATTERN.search(
                str(ctx.get("errorMessage", ""))
            )
            is not None,
            "wrapStreamFn": lambda ctx: create_deep_seek_v4_thinking_wrapper(
                ctx.get("streamFn"),
                ctx.get("thinkingLevel"),
            ),
            "resolveThinkingProfile": lambda ctx: resolve_deep_seek_v4_thinking_profile(
                str(ctx.get("modelId", ""))
            ),
            "isModernModelRef": lambda ctx: resolve_deep_seek_v4_thinking_profile(
                str(ctx.get("modelId", ""))
            )
            is not None,
            "applyConfig": apply_deep_seek_config,
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="DeepSeek Provider",
    description="Bundled DeepSeek provider plugin",
    register=_register,
)
