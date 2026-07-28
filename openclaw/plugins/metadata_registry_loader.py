from __future__ import annotations

from typing import Any


def resolve_metadata_registry_loader(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "entries": {},
        "loaded": False,
    }


def load_metadata_registry(
    loader: dict[str, Any],
    entries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    loader["entries"] = entries or {}
    loader["loaded"] = True
    return loader
