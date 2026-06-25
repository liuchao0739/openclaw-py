"""Channel id normalization through the active plugin registry."""

from __future__ import annotations

from typing import Any


def normalize_any_channel_id(raw: str | None) -> str | None:
    """Normalize user/config channel identifiers so aliases resolve to canonical channel ids."""
    if not raw:
        return None
    key = raw.strip().lower()
    if not key:
        return None
    try:
        from openclaw.channels.registry_lookup import find_registered_channel_plugin_entry

        entry = find_registered_channel_plugin_entry(key)
        if entry:
            plugin = entry.get("plugin", {})
            plugin_id = plugin.get("id")
            if plugin_id:
                return plugin_id
    except Exception:
        pass
    return None
