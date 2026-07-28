from __future__ import annotations

from typing import Any


class PluginKind:
    BUNDLED = "bundled"
    EXTERNAL = "external"
    OVERLAY = "overlay"


def resolve_plugin_kind(
    plugin_id: str,
    config: dict[str, Any] | None = None,
) -> str:
    config = config or {}
    bundled = config.get("bundledPlugins", [])
    if plugin_id in bundled:
        return PluginKind.BUNDLED
    return PluginKind.EXTERNAL
