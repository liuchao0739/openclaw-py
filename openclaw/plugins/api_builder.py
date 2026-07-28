from __future__ import annotations

from typing import Any


def build_plugin_api_builder(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "endpoints": {},
    }


def add_api_endpoint(
    builder: dict[str, Any],
    path: str,
    handler: Any,
) -> dict[str, Any]:
    builder.setdefault("endpoints", {})[path] = handler
    return builder
