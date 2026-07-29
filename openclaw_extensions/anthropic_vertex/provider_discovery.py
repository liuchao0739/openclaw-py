import os
from typing import Any, Mapping, Optional

from .region import (
    has_anthropic_vertex_available_auth,
    resolve_anthropic_vertex_config_api_key,
)
from .provider_catalog import build_anthropic_vertex_provider

PROVIDER_ID = "anthropic-vertex"
GCP_VERTEX_CREDENTIALS_MARKER = "gcp-vertex-credentials"


def _merge_implicit_anthropic_vertex_provider(params: dict) -> dict:
    existing = params.get("existing")
    implicit = params["implicit"]
    if not existing:
        return implicit
    merged = {**implicit, **existing}
    existing_models = existing.get("models")
    if isinstance(existing_models, list) and len(existing_models) > 0:
        merged["models"] = existing_models
    else:
        merged["models"] = implicit.get("models")
    return merged


def _resolve_implicit_anthropic_vertex_provider(params: Optional[dict] = None) -> Optional[dict]:
    params = params or {}
    env = params.get("env") if params.get("env") is not None else os.environ
    if not has_anthropic_vertex_available_auth(env):
        return None
    return build_anthropic_vertex_provider({"env": env})


async def _run_anthropic_vertex_catalog(ctx: dict) -> Optional[dict]:
    implicit = _resolve_implicit_anthropic_vertex_provider({"env": ctx.get("env")})
    if not implicit:
        return None
    config = ctx.get("config") or {}
    models = config.get("models") if isinstance(config, dict) else None
    providers = models.get("providers") if isinstance(models, dict) else None
    existing = providers.get(PROVIDER_ID) if isinstance(providers, dict) else None
    return {
        "provider": _merge_implicit_anthropic_vertex_provider({
            "existing": existing,
            "implicit": implicit,
        })
    }


def _resolve_synthetic_auth() -> Optional[dict]:
    if not has_anthropic_vertex_available_auth():
        return None
    return {
        "apiKey": GCP_VERTEX_CREDENTIALS_MARKER,
        "source": "gcp-vertex-credentials (ADC)",
        "mode": "api-key",
    }


anthropic_vertex_provider_discovery = {
    "id": PROVIDER_ID,
    "label": "Anthropic Vertex",
    "docsPath": "/providers/models",
    "auth": [],
    "catalog": {
        "order": "simple",
        "run": _run_anthropic_vertex_catalog,
    },
    "resolveConfigApiKey": lambda params: resolve_anthropic_vertex_config_api_key(params.get("env")),
    "resolveSyntheticAuth": _resolve_synthetic_auth,
}
