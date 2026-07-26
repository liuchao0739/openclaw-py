"""Provider discovery descriptor for Anthropic Vertex."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.anthropic_vertex.api import (
    merge_implicit_anthropic_vertex_provider,
    resolve_implicit_anthropic_vertex_provider,
)
from openclaw_extensions.anthropic_vertex.provider_catalog import build_anthropic_vertex_provider
from openclaw_extensions.anthropic_vertex.region import (
    GCP_VERTEX_CREDENTIALS_MARKER,
    has_anthropic_vertex_available_auth,
    resolve_anthropic_vertex_config_api_key,
)

PROVIDER_ID = "anthropic-vertex"


async def _run_anthropic_vertex_catalog(ctx: dict[str, Any]) -> dict[str, Any] | None:
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


anthropic_vertex_provider_discovery: dict[str, Any] = {
    "id": PROVIDER_ID,
    "label": "Anthropic Vertex",
    "docsPath": "/providers/models",
    "auth": [],
    "catalog": {
        "order": "simple",
        "run": _run_anthropic_vertex_catalog,
    },
    "resolveConfigApiKey": lambda params: resolve_anthropic_vertex_config_api_key(params.get("env")),
    "resolveSyntheticAuth": lambda _ctx=None: (
        {
            "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
            "source": "gcp-vertex-credentials (ADC)",
            "mode": "api-key",
        }
        if has_anthropic_vertex_available_auth()
        else None
    ),
}

default = anthropic_vertex_provider_discovery

__all__ = ["anthropic_vertex_provider_discovery", "build_anthropic_vertex_provider", "default"]
