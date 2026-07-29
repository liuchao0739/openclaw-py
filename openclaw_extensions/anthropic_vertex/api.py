from typing import Any, Optional

from .provider_catalog import (
    ANTHROPIC_VERTEX_DEFAULT_MODEL_ID,
    build_anthropic_vertex_provider,
)
from .region import (
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
    "has_anthropic_vertex_available_auth",
    "has_anthropic_vertex_credentials",
    "resolve_anthropic_vertex_client_region",
    "resolve_anthropic_vertex_config_api_key",
    "resolve_anthropic_vertex_project_id",
    "resolve_anthropic_vertex_region",
    "resolve_anthropic_vertex_region_from_base_url",
    "merge_implicit_anthropic_vertex_provider",
    "resolve_implicit_anthropic_vertex_provider",
    "create_anthropic_vertex_stream_fn",
    "create_anthropic_vertex_stream_fn_for_model",
]

_stream_runtime_module = None


def _load_stream_runtime_module():
    global _stream_runtime_module
    if _stream_runtime_module is None:
        from . import stream_runtime as _stream_runtime_module
    return _stream_runtime_module


def merge_implicit_anthropic_vertex_provider(params: dict) -> dict:
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


def resolve_implicit_anthropic_vertex_provider(params: Optional[dict] = None) -> Optional[dict]:
    import os

    params = params or {}
    env = params.get("env") if params.get("env") is not None else os.environ
    if not has_anthropic_vertex_available_auth(env):
        return None
    return build_anthropic_vertex_provider({"env": env})


def create_anthropic_vertex_stream_fn(project_id, region, base_url=None, deps=None):
    runtime = _load_stream_runtime_module()
    stream_fn = runtime.create_anthropic_vertex_stream_fn(project_id, region, base_url, deps)

    def _stream(model, context, options=None):
        return stream_fn(model, context, options)

    return _stream


def create_anthropic_vertex_stream_fn_for_model(model, env=None, deps=None):
    import os

    if env is None:
        env = os.environ
    runtime = _load_stream_runtime_module()
    stream_fn = runtime.create_anthropic_vertex_stream_fn_for_model(model, env, deps)

    def _stream(*args):
        return stream_fn(*args)

    return _stream
