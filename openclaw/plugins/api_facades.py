from __future__ import annotations

from typing import Any


def build_plugin_api_facades(
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "runtime": runtime or {},
        "apis": {},
    }


def register_plugin_api(
    facades: dict[str, Any],
    api_id: str,
    implementation: Any,
) -> dict[str, Any]:
    facades.setdefault("apis", {})[api_id] = implementation
    return facades
