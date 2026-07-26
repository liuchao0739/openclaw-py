"""Synchronous Amazon Bedrock Mantle provider registration."""

from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi
from openclaw_extensions.amazon_bedrock_mantle.discovery import (
    merge_implicit_mantle_provider,
    resolve_implicit_mantle_provider,
    resolve_mantle_bearer_token,
    resolve_mantle_runtime_bearer_token,
)
from openclaw_extensions.amazon_bedrock_mantle.mantle_anthropic_runtime import (
    create_mantle_anthropic_stream_fn,
)

_PROVIDER_ID = "amazon-bedrock-mantle"
_CONTEXT_OVERFLOW_PATTERN = re.compile(
    r"context_length_exceeded|max.*tokens.*exceeded",
    re.IGNORECASE,
)
_RATE_LIMIT_PATTERN = re.compile(r"rate_limit|too many requests|429", re.IGNORECASE)
_OVERLOADED_PATTERN = re.compile(r"overloaded|503|service.*unavailable", re.IGNORECASE)


def _resolve_plugin_config_object(
    config: dict[str, Any] | None,
    plugin_id: str,
) -> dict[str, Any] | None:
    if not is_record(config):
        return None
    plugins = config.get("plugins")
    if not is_record(plugins):
        return None
    entries = plugins.get("entries")
    if not is_record(entries):
        return None
    entry = entries.get(plugin_id)
    if not is_record(entry):
        return None
    plugin_config = entry.get("config")
    return plugin_config if is_record(plugin_config) else None


def register_bedrock_mantle_plugin(api: OpenClawPluginApi) -> None:
    """Register the Amazon Bedrock Mantle provider with OpenClaw."""
    startup_plugin_config = api.plugin_config if is_record(api.plugin_config) else {}

    def resolve_current_plugin_config(
        config: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        runtime_plugin_config = _resolve_plugin_config_object(config, _PROVIDER_ID)
        if runtime_plugin_config is not None:
            return runtime_plugin_config
        return startup_plugin_config if config is None else None

    async def catalog_run(ctx: dict[str, Any]) -> dict[str, Any] | None:
        current_plugin_config = resolve_current_plugin_config(ctx.get("config"))
        implicit = await resolve_implicit_mantle_provider(
            {
                "env": ctx.get("env"),
                "pluginConfig": current_plugin_config,
            }
        )
        if not implicit:
            return None

        config = ctx.get("config") if is_record(ctx.get("config")) else {}
        models = config.get("models") if is_record(config.get("models")) else {}
        providers = models.get("providers") if is_record(models.get("providers")) else {}
        existing = providers.get(_PROVIDER_ID) if is_record(providers.get(_PROVIDER_ID)) else None
        return {
            "provider": merge_implicit_mantle_provider(
                {
                    "existing": existing,
                    "implicit": implicit,
                }
            ),
        }

    def resolve_config_api_key(ctx: dict[str, Any]) -> str | None:
        env = ctx.get("env") if is_record(ctx.get("env")) else {}
        return "env:AWS_BEARER_TOKEN_BEDROCK" if resolve_mantle_bearer_token(env) else None

    async def prepare_runtime_auth(ctx: dict[str, Any]) -> dict[str, Any] | None:
        return await resolve_mantle_runtime_bearer_token(
            {
                "apiKey": ctx.get("apiKey"),
                "env": ctx.get("env"),
            }
        )

    def create_stream_fn(ctx: dict[str, Any]) -> Any:
        model = ctx.get("model")
        if isinstance(model, dict) and model.get("api") == "anthropic-messages":
            return create_mantle_anthropic_stream_fn()
        return None

    def matches_context_overflow_error(ctx: dict[str, Any]) -> bool:
        return bool(_CONTEXT_OVERFLOW_PATTERN.search(str(ctx.get("errorMessage", ""))))

    def classify_failover_reason(ctx: dict[str, Any]) -> str | None:
        error_message = str(ctx.get("errorMessage", ""))
        if _RATE_LIMIT_PATTERN.search(error_message):
            return "rate_limit"
        if _OVERLOADED_PATTERN.search(error_message):
            return "overloaded"
        return None

    api.register_provider(
        {
            "id": _PROVIDER_ID,
            "label": "Amazon Bedrock Mantle (OpenAI-compatible)",
            "docsPath": "/providers/bedrock-mantle",
            "auth": [],
            "catalog": {
                "order": "simple",
                "run": catalog_run,
            },
            "resolveConfigApiKey": resolve_config_api_key,
            "prepareRuntimeAuth": prepare_runtime_auth,
            "createStreamFn": create_stream_fn,
            "matchesContextOverflowError": matches_context_overflow_error,
            "classifyFailoverReason": classify_failover_reason,
        }
    )
