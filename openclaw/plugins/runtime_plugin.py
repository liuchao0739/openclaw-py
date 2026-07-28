from __future__ import annotations

from typing import Any


def build_runtime_plugin_entry(
    plugin_id: str,
    manifest: dict[str, Any],
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "name": manifest.get("name", plugin_id),
        "version": manifest.get("version", "0.0.0"),
        "entry": manifest.get("entry"),
        "runtimeConfig": runtime_config or {},
        "enabled": True,
    }


def resolve_runtime_plugin_state(
    plugin_id: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or {}
    return {
        "pluginId": plugin_id,
        "enabled": state.get("enabled", True),
        "loaded": state.get("loaded", False),
        "error": state.get("error"),
    }
