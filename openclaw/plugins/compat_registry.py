from __future__ import annotations

from typing import Any


def build_plugin_compat_registry(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "entries": {},
        "version": 1,
    }


def register_plugin_compat(
    registry: dict[str, Any],
    plugin_id: str,
    status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    registry.setdefault("entries", {})[plugin_id] = {
        "status": status,
        "reason": reason,
        "updatedAt": __import__("time").time(),
    }
    return registry
