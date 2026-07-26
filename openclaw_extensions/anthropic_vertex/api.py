"""Public Anthropic Vertex API barrel."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from openclaw_extensions.anthropic_vertex.provider_catalog import (
    ANTHROPIC_VERTEX_DEFAULT_MODEL_ID,
    build_anthropic_vertex_provider,
)
from openclaw_extensions.anthropic_vertex.region import (
    has_anthropic_vertex_available_auth,
    has_anthropic_vertex_credentials,
    resolve_anthropic_vertex_client_region,
    resolve_anthropic_vertex_config_api_key,
    resolve_anthropic_vertex_project_id,
    resolve_anthropic_vertex_region,
    resolve_anthropic_vertex_region_from_base_url,
)

__all__ = [
    "ANTHROPIC_VERTEX_DEFAULT_MODEL_ID",
    "build_anthropic_vertex_provider",
    "create_anthropic_vertex_stream_fn",
    "create_anthropic_vertex_stream_fn_for_model",
    "has_anthropic_vertex_available_auth",
    "has_anthropic_vertex_credentials",
    "merge_implicit_anthropic_vertex_provider",
    "resolve_anthropic_vertex_client_region",
    "resolve_anthropic_vertex_config_api_key",
    "resolve_anthropic_vertex_project_id",
    "resolve_anthropic_vertex_region",
    "resolve_anthropic_vertex_region_from_base_url",
    "resolve_implicit_anthropic_vertex_provider",
]

_stream_runtime_module: Any = None


def _load_stream_runtime_module() -> Any:
    global _stream_runtime_module
    if _stream_runtime_module is None:
        _stream_runtime_module = importlib.import_module(
            "openclaw_extensions.anthropic_vertex.stream_runtime"
        )
    return _stream_runtime_module


def merge_implicit_anthropic_vertex_provider(params: dict[str, Any]) -> dict[str, Any]:
    """Merge an implicit Anthropic Vertex provider with explicit user config."""
    existing = params.get("existing")
    implicit = params["implicit"]
    if not existing:
        return implicit
    existing_models = existing.get("models") if isinstance(existing, dict) else None
    return {
        **implicit,
        **existing,
        "models": existing_models if isinstance(existing_models, list) and existing_models else implicit.get("models"),
    }


def resolve_implicit_anthropic_vertex_provider(
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Resolve an implicit Anthropic Vertex provider when ADC credentials are available."""
    env = params.get("env") if params else None
    if not has_anthropic_vertex_available_auth(env):
        return None
    return build_anthropic_vertex_provider({"env": env})


def create_anthropic_vertex_stream_fn(
    project_id: str | None,
    region: str,
    base_url: str | None = None,
    deps: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Create a lazy Anthropic Vertex stream function for a known project/region/base URL."""
    runtime = _load_stream_runtime_module()
    stream_fn = runtime.create_anthropic_vertex_stream_fn(project_id, region, base_url, deps)

    def lazy_stream_fn(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        return stream_fn(model, context, options)

    return lazy_stream_fn


def create_anthropic_vertex_stream_fn_for_model(
    model: dict[str, Any],
    env: dict[str, str] | None = None,
    deps: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Create a lazy Anthropic Vertex stream function using model base URL and env hints."""
    runtime = _load_stream_runtime_module()
    stream_fn = runtime.create_anthropic_vertex_stream_fn_for_model(model, env, deps)

    def lazy_stream_fn(model_arg: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        return stream_fn(model_arg, context, options)

    return lazy_stream_fn
