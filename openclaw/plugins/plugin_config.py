from __future__ import annotations

from typing import Any


def build_plugin_config(
    plugin_id: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "manifest": manifest or {},
        "config": {},
        "enabled": True,
    }


def load_plugin_config_for_id(
    plugin_id: str,
    configs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    configs = configs or {}
    return configs.get(plugin_id, build_plugin_config(plugin_id))
