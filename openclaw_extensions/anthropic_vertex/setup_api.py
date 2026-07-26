"""Lightweight Anthropic Vertex setup entry."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry
from openclaw_extensions.anthropic_vertex.region import resolve_anthropic_vertex_config_api_key

PROVIDER_ID = "anthropic-vertex"


def _register(api: Any) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Anthropic Vertex",
            "auth": [],
            "resolveConfigApiKey": lambda params: resolve_anthropic_vertex_config_api_key(
                params.get("env")
            ),
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Anthropic Vertex Setup",
    description="Lightweight Anthropic Vertex setup hooks",
    register=_register,
)
