"""Anthropic Vertex provider extension."""

from openclaw_extensions.anthropic_vertex.api import (
    ANTHROPIC_VERTEX_DEFAULT_MODEL_ID,
    build_anthropic_vertex_provider,
    create_anthropic_vertex_stream_fn,
    create_anthropic_vertex_stream_fn_for_model,
    has_anthropic_vertex_available_auth,
    has_anthropic_vertex_credentials,
    merge_implicit_anthropic_vertex_provider,
    resolve_anthropic_vertex_client_region,
    resolve_anthropic_vertex_config_api_key,
    resolve_anthropic_vertex_project_id,
    resolve_anthropic_vertex_region,
    resolve_anthropic_vertex_region_from_base_url,
    resolve_implicit_anthropic_vertex_provider,
)
from openclaw_extensions.anthropic_vertex.provider_catalog import (
    normalize_anthropic_vertex_resolved_model,
)
from openclaw_extensions.anthropic_vertex.provider_discovery import (
    anthropic_vertex_provider_discovery,
)
from openclaw_extensions.anthropic_vertex.provider_policy_api import resolve_thinking_profile

__all__ = [
    "ANTHROPIC_VERTEX_DEFAULT_MODEL_ID",
    "anthropic_vertex_provider_discovery",
    "build_anthropic_vertex_provider",
    "create_anthropic_vertex_stream_fn",
    "create_anthropic_vertex_stream_fn_for_model",
    "has_anthropic_vertex_available_auth",
    "has_anthropic_vertex_credentials",
    "merge_implicit_anthropic_vertex_provider",
    "normalize_anthropic_vertex_resolved_model",
    "resolve_anthropic_vertex_client_region",
    "resolve_anthropic_vertex_config_api_key",
    "resolve_anthropic_vertex_project_id",
    "resolve_anthropic_vertex_region",
    "resolve_anthropic_vertex_region_from_base_url",
    "resolve_implicit_anthropic_vertex_provider",
    "resolve_thinking_profile",
]
