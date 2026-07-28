from __future__ import annotations

from typing import Any


def build_gateway_request_scope(
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "request": request or {},
        "pluginId": None,
        "sessionId": None,
        "metadata": {},
    }


def resolve_gateway_plugin_id(
    scope: dict[str, Any],
) -> str | None:
    return scope.get("pluginId")
