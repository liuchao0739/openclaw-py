from __future__ import annotations

from typing import Any


def resolve_discovery(
    config: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "options": options or {},
        "plugins": [],
        "sources": [],
    }


def discover_plugins(
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or {}
    return []
