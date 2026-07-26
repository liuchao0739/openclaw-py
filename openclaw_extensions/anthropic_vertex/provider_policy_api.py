"""Provider-policy API for Anthropic Vertex."""

from __future__ import annotations

from typing import Any

from openclaw_extensions.anthropic_vertex.claude_thinking import resolve_claude_thinking_profile


def resolve_thinking_profile(params: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve Anthropic Vertex thinking profile for a provider/model pair."""
    provider = str(params.get("provider", "")).strip().lower()
    if provider != "anthropic-vertex":
        return None
    model_params = params.get("params")
    return resolve_claude_thinking_profile(
        str(params.get("modelId", "")),
        model_params if isinstance(model_params, dict) else None,
        include_native_max=True,
    )
