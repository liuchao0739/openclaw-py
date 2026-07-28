from __future__ import annotations

from typing import Any


def build_plugin_activation_context(
    plugin_id: str,
    manifest: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "manifest": manifest,
        "config": config or {},
        "activatedAt": __import__("time").time(),
    }


def activate_plugin(
    context: dict[str, Any],
) -> dict[str, Any]:
    context["active"] = True
    return context
