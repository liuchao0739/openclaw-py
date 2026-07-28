from __future__ import annotations

from typing import Any


def build_runtime_cache() -> dict[str, Any]:
    return {
        "entries": {},
        "maxSize": 1000,
        "ttlMs": 3600000,
    }


def get_runtime_cache_entry(
    cache: dict[str, Any],
    key: str,
) -> Any:
    entries = cache.get("entries", {})
    return entries.get(key)


def set_runtime_cache_entry(
    cache: dict[str, Any],
    key: str,
    value: Any,
) -> dict[str, Any]:
    cache.setdefault("entries", {})[key] = value
    return cache
