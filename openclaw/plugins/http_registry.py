from __future__ import annotations

from typing import Any


def build_http_registry(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "routes": {},
        "middleware": [],
    }


def register_http_route(
    registry: dict[str, Any],
    method: str,
    path: str,
    handler: Any,
) -> dict[str, Any]:
    key = f"{method.upper()}:{path}"
    registry.setdefault("routes", {})[key] = handler
    return registry
