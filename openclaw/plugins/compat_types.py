from __future__ import annotations

from typing import Any


class PluginCompatStatus:
    COMPAT = "compat"
    DEPRECATED = "deprecated"
    REMOVED = "removed"
    BLOCKED = "blocked"


class PluginManifestFormat:
    V1 = "v1"
    V2 = "v2"


PLUGIN_COMPAT_STATUSES: set[str] = {
    PluginCompatStatus.COMPAT,
    PluginCompatStatus.DEPRECATED,
    PluginCompatStatus.REMOVED,
    PluginCompatStatus.BLOCKED,
}


def normalize_plugin_compat_status(value: Any) -> str:
    if isinstance(value, str) and value in PLUGIN_COMPAT_STATUSES:
        return value
    return PluginCompatStatus.BLOCKED
