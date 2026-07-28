from __future__ import annotations

from typing import Any


def build_current_plugin_metadata_state(
    plugins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "plugins": plugins or [],
        "timestamp": __import__("time").time(),
        "version": 1,
    }


def resolve_current_plugin_metadata_snapshot(
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or {}
    return {
        "plugins": state.get("plugins", []),
        "timestamp": state.get("timestamp"),
    }
