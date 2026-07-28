from __future__ import annotations

from typing import Any


class PluginOrigin:
    BUNDLED = "bundled"
    NPM = "npm"
    GIT = "git"
    PATH = "path"
    MARKETPLACE = "marketplace"
    MANUAL = "manual"


def resolve_plugin_origin(
    plugin_id: str,
    install_records: dict[str, Any] | None = None,
) -> str:
    install_records = install_records or {}
    record = install_records.get(plugin_id)
    if record:
        return record.get("source", PluginOrigin.MANUAL)
    return PluginOrigin.BUNDLED
