from __future__ import annotations

from typing import Any


def resolve_native_deps(
    plugin_id: str,
    config: dict[str, Any] | None = None,
) -> list[str]:
    config = config or {}
    return config.get("nativeDeps", [])
