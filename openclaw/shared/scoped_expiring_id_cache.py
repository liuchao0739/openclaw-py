"""Per-scope TTL cache to suppress repeated ids without cross-scope bleed."""

from __future__ import annotations

import time
from typing import Any


def _resolve_non_negative_integer(value: float, fallback: int) -> int:
    if value >= 0 and value == int(value):
        return max(0, int(value))
    return fallback


def create_scoped_expiring_id_cache(
    store: dict[str, dict[str, float]],
    ttl_ms: float,
    cleanup_threshold: int,
) -> dict[str, Any]:
    ttl = _resolve_non_negative_integer(ttl_ms, 0)
    threshold = max(1, _resolve_non_negative_integer(cleanup_threshold, 1))

    def _cleanup_expired(scope_key: str, entry: dict[str, float], now: float) -> None:
        expired_ids: list[str] = []
        for id_key, timestamp in entry.items():
            if now - timestamp > ttl:
                expired_ids.append(id_key)
        for id_key in expired_ids:
            del entry[id_key]
        if len(entry) == 0:
            store.pop(scope_key, None)

    def _record(scope: Any, id_value: Any, now: float | None = None) -> None:
        if now is None:
            now = time.time() * 1000
        scope_key = str(scope)
        id_key = str(id_value)
        entry = store.get(scope_key)
        if entry is None:
            entry = {}
            store[scope_key] = entry
        entry[id_key] = now
        if len(entry) > threshold:
            _cleanup_expired(scope_key, entry, now)

    def _has(scope: Any, id_value: Any, now: float | None = None) -> bool:
        if now is None:
            now = time.time() * 1000
        scope_key = str(scope)
        id_key = str(id_value)
        entry = store.get(scope_key)
        if entry is None:
            return False
        _cleanup_expired(scope_key, entry, now)
        return id_key in entry

    def _clear() -> None:
        store.clear()

    return {"record": _record, "has": _has, "clear": _clear}
