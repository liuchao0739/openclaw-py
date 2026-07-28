from __future__ import annotations

from typing import Any


def resolve_channel_registry_state(
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or {}
    return {
        "channels": state.get("channels", {}),
        "version": state.get("version", 1),
    }


def update_channel_registry_state(
    channel_id: str,
    plugin_id: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or {}
    channels = state.setdefault("channels", {})
    channels[channel_id] = {
        "pluginId": plugin_id,
        "active": True,
    }
    return state
