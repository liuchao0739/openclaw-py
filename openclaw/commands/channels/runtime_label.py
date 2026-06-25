"""Runtime-aware channel label lookup for command output."""

from __future__ import annotations

from typing import Any


def _get_loaded_channel_plugin(channel: str) -> dict[str, Any] | None:
    try:
        from openclaw.channels.plugins.registry import get_loaded_channel_plugin

        return get_loaded_channel_plugin(channel)
    except Exception:
        return None


def _get_bundled_channel_setup_plugin(channel: str) -> dict[str, Any] | None:
    try:
        from openclaw.channels.plugins.bundled import get_bundled_channel_setup_plugin

        return get_bundled_channel_setup_plugin(channel)
    except Exception:
        return None


def _get_channel_plugin(channel: str) -> dict[str, Any] | None:
    try:
        from openclaw.channels.plugins.registry import get_channel_plugin

        return get_channel_plugin(channel)
    except Exception:
        return None


def channel_label(channel: str) -> str:
    """Resolve a display label from loaded, setup-only, or bundled channel plugin metadata."""
    plugin = (
        _get_loaded_channel_plugin(channel)
        or _get_bundled_channel_setup_plugin(channel)
        or _get_channel_plugin(channel)
    )
    if plugin:
        meta = plugin.get("meta", {}) if isinstance(plugin, dict) else getattr(plugin, "meta", None)
        if meta:
            label = meta.get("label") if isinstance(meta, dict) else getattr(meta, "label", None)
            if label:
                return label
    return channel
