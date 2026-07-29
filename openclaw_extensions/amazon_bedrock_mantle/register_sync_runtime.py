import re
from typing import Any, Dict, Optional

from .discovery import (
    merge_implicit_mantle_provider,
    resolve_implicit_mantle_provider,
    resolve_mantle_bearer_token,
    resolve_mantle_runtime_bearer_token,
)
from .mantle_anthropic_runtime import create_mantle_anthropic_stream_fn

PROVIDER_ID = "amazon-bedrock-mantle"


def _resolve_plugin_config_object(config: Optional[Dict[str, Any]], provider_id: str) -> Optional[Dict[str, Any]]:
    if not config:
        return None
    plugins = config.get("plugins") or {}
    entry = plugins.get(provider_id)
    if isinstance(entry, dict):
        return entry.get("config")
    return None


def register_bedrock_mantle_plugin(api: Any) -> None:
    startup_plugin_config = getattr(api, "pluginConfig", None) or {}

    def resolve_current_plugin_config(config: Optional[Dict[str, Any]]):
        runtime_plugin_config = _resolve_plugin_config_object(config, PROVIDER_ID)
        if runtime_plugin_config is not None:
            return runtime_plugin_config
        return startup_plugin_config if config is None else None

    async def catalog_run(ctx: Any):
        current_plugin_config = resolve_current_plugin_config(getattr(ctx, "config", None))
        implicit = await resolve_implicit_mantle_provider(
            {
                "env": getattr(ctx, "env", None),
                "pluginConfig": current_plugin_config,
            }
        )
        if not implicit:
            return None
        providers = ((getattr(ctx.config, "models", None) or {}).get("providers") or {}) if hasattr(ctx, "config") else {}
        existing = providers.get(PROVIDER_ID)
        return {
            "provider": merge_implicit_mantle_provider(
                {"existing": existing, "implicit": implicit}
            )
        }

    def resolve_config_api_key(ctx: Any):
        env = getattr(ctx, "env", None)
        return "env:AWS_BEARER_TOKEN_BEDROCK" if resolve_mantle_bearer_token(env) else None

    async def prepare_runtime_auth(ctx: Any):
        return await resolve_mantle_runtime_bearer_token(
            {
                "apiKey": getattr(ctx, "apiKey", ""),
                "env": getattr(ctx, "env", None),
            }
        )

    def create_stream_fn(ctx: Any):
        model = getattr(ctx, "model", None)
        if model and getattr(model, "api", None) == "anthropic-messages":
            return create_mantle_anthropic_stream_fn()
        return None

    def matches_context_overflow_error(ctx: Any):
        message = getattr(ctx, "errorMessage", "") or ""
        return bool(re.search(r"context_length_exceeded|max.*tokens.*exceeded", message, re.I))

    def classify_failover_reason(ctx: Any):
        message = getattr(ctx, "errorMessage", "") or ""
        if re.search(r"rate_limit|too many requests|429", message, re.I):
            return "rate_limit"
        if re.search(r"overloaded|503|service.*unavailable", message, re.I):
            return "overloaded"
        return None

    api.registerProvider(
        {
            "id": PROVIDER_ID,
            "label": "Amazon Bedrock Mantle (OpenAI-compatible)",
            "docsPath": "/providers/bedrock-mantle",
            "auth": [],
            "catalog": {"order": "simple", "run": catalog_run},
            "resolveConfigApiKey": resolve_config_api_key,
            "prepareRuntimeAuth": prepare_runtime_auth,
            "createStreamFn": create_stream_fn,
            "matchesContextOverflowError": matches_context_overflow_error,
            "classifyFailoverReason": classify_failover_reason,
        }
    )
