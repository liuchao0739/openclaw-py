from __future__ import annotations

from typing import Any


def build_runtime_plugins(
    plugins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "plugins": plugins or [],
        "active": {},
        "state": {},
    }


def activate_plugin(
    runtime_plugins: dict[str, Any],
    plugin_id: str,
) -> dict[str, Any]:
    runtime_plugins.setdefault("active", {})[plugin_id] = True
    return runtime_plugins


def deactivate_plugin(
    runtime_plugins: dict[str, Any],
    plugin_id: str,
) -> dict[str, Any]:
    runtime_plugins.setdefault("active", {})[plugin_id] = False
    return runtime_plugins
