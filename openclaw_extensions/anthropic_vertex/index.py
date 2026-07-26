"""Anthropic Vertex provider plugin entry."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.anthropic_vertex.api import (
    has_anthropic_vertex_available_auth,
    merge_implicit_anthropic_vertex_provider,
    resolve_anthropic_vertex_config_api_key,
    resolve_implicit_anthropic_vertex_provider,
)
from openclaw_extensions.anthropic_vertex.claude_thinking import resolve_claude_thinking_profile
from openclaw_extensions.anthropic_vertex.provider_catalog import (
    normalize_anthropic_vertex_resolved_model,
    read_configured_provider_catalog_entries,
)
from openclaw_extensions.anthropic_vertex.region import GCP_VERTEX_CREDENTIALS_MARKER
from openclaw_extensions.anthropic_vertex.replay_hooks import NATIVE_ANTHROPIC_REPLAY_HOOKS

PROVIDER_ID = "anthropic-vertex"


async def _catalog_run(ctx: dict[str, Any]) -> dict[str, Any] | None:
    implicit = resolve_implicit_anthropic_vertex_provider({"env": ctx.get("env")})
    if not implicit:
        return None
    config = ctx.get("config")
    existing = None
    if isinstance(config, dict):
        providers = config.get("models", {}).get("providers")
        if isinstance(providers, dict):
            existing = providers.get(PROVIDER_ID)
    return {
        "provider": merge_implicit_anthropic_vertex_provider(
            {"existing": existing, "implicit": implicit}
        ),
    }


def _register(api: Any) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Anthropic Vertex",
            "docsPath": "/providers/models",
            "auth": [],
            "catalog": {
                "order": "simple",
                "run": _catalog_run,
            },
            "resolveConfigApiKey": lambda params: resolve_anthropic_vertex_config_api_key(
                params.get("env")
            ),
            **NATIVE_ANTHROPIC_REPLAY_HOOKS,
            "normalizeResolvedModel": lambda ctx: normalize_anthropic_vertex_resolved_model(
                str(ctx.get("modelId", "")),
                ctx.get("model") if isinstance(ctx.get("model"), dict) else {},
            ),
            "resolveThinkingProfile": lambda ctx: resolve_claude_thinking_profile(
                str(ctx.get("modelId", "")),
                ctx.get("params") if isinstance(ctx.get("params"), dict) else None,
                include_native_max=True,
            ),
            "resolveSyntheticAuth": lambda _ctx=None: (
                {
                    "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
                    "source": "gcp-vertex-credentials (ADC)",
                    "mode": "api-key",
                }
                if has_anthropic_vertex_available_auth()
                else None
            ),
            "augmentModelCatalog": lambda ctx: read_configured_provider_catalog_entries(
                {
                    "config": ctx.get("config"),
                    "providerId": PROVIDER_ID,
                }
            ),
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Anthropic Vertex Provider",
    description="Bundled Anthropic Vertex provider plugin",
    register=_register,
)
