from __future__ import annotations

from typing import Any


def build_default_enablement(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "enabled": True,
        "plugins": {},
        "config": config or {},
    }


def resolve_plugin_enablement(
    plugin_id: str,
    enablement: dict[str, Any] | None = None,
) -> bool:
    enablement = enablement or build_default_enablement()
    plugin_config = enablement.get("plugins", {}).get(plugin_id, {})
    if "enabled" in plugin_config:
        return plugin_config["enabled"]
    return enablement.get("enabled", True)
