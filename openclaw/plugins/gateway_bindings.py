from __future__ import annotations

from typing import Any


def resolve_gateway_bindings(
    plugins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "routes": [],
        "middleware": [],
        "plugins": plugins or [],
    }


def register_gateway_route(
    bindings: dict[str, Any],
    path: str,
    handler: Any,
    **options: Any,
) -> dict[str, Any]:
    routes = bindings.setdefault("routes", [])
    routes.append({
        "path": path,
        "handler": handler,
        **options,
    })
    return bindings
