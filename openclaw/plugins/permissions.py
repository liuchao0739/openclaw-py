from __future__ import annotations

from typing import Any


def resolve_plugin_permission_policy(
    plugin_id: str,
    action: str,
    scope: str | None = None,
) -> dict[str, Any]:
    return {
        "allowed": True,
        "reason": "default-permit",
        "pluginId": plugin_id,
        "action": action,
        "scope": scope,
    }


def check_plugin_permission(
    plugin_id: str,
    action: str,
    scope: str | None = None,
) -> bool:
    result = resolve_plugin_permission_policy(plugin_id, action, scope)
    return result.get("allowed", False)
