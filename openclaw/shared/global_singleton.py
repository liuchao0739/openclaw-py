"""Process-local singleton helpers for registries, caches, and shared state."""

from __future__ import annotations

import threading
from typing import Any, Callable


_global_store: dict[str, Any] = {}
_global_lock = threading.Lock()


def resolve_global_singleton(key: str, create: Callable[[], Any]) -> Any:
    with _global_lock:
        if key in _global_store:
            return _global_store[key]
        created = create()
        _global_store[key] = created
        return created


def resolve_global_map(key: str) -> dict:
    return resolve_global_singleton(key, lambda: {})
