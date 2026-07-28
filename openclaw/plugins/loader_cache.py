from __future__ import annotations

from typing import Any


def resolve_plugin_loader_cache(
    plugin_id: str,
    version: str,
) -> dict[str, Any] | None:
    return None


def set_plugin_loader_cache(
    plugin_id: str,
    version: str,
    entry: dict[str, Any],
) -> None:
    pass


def clear_plugin_loader_cache(plugin_id: str | None = None) -> None:
    pass
