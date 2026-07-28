from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from openclaw_extensions.active_memory.config import (
    CACHE_SWEEP_INTERVAL_MS,
    DEFAULT_MAX_CACHE_ENTRIES,
)


@dataclass
class CachedActiveRecallResult:
    expires_at: float
    result: Any


_active_recall_cache: dict[str, CachedActiveRecallResult] = {}
_last_active_recall_cache_sweep_at: float = 0.0


def build_cache_key(agent_id: str, session_key: str | None, session_id: str | None, query: str) -> str:
    hash_digest = hashlib.sha1(query.encode("utf-8")).hexdigest()
    session_part = session_key or session_id or "none"
    return f"{agent_id}:{session_part}:{hash_digest}"


def _as_date_timestamp_ms(value: float) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _resolve_expires_at_ms_from_duration_ms(ttl_ms: int, now_ms: float) -> float | None:
    try:
        return now_ms + float(ttl_ms)
    except (ValueError, TypeError):
        return None


def get_cached_result(cache_key: str) -> Any | None:
    cached = _active_recall_cache.get(cache_key)
    if cached is None:
        return None
    now = time.time() * 1000
    expires_at = _as_date_timestamp_ms(cached.expires_at)
    if expires_at is None or expires_at <= now:
        _active_recall_cache.pop(cache_key, None)
        return None
    return cached.result


def set_cached_result(cache_key: str, result: Any, ttl_ms: int) -> None:
    global _last_active_recall_cache_sweep_at
    raw_now = time.time() * 1000
    now = _as_date_timestamp_ms(raw_now)

    if (
        len(_active_recall_cache) >= DEFAULT_MAX_CACHE_ENTRIES
        or (now is not None and now - _last_active_recall_cache_sweep_at >= CACHE_SWEEP_INTERVAL_MS)
    ):
        _sweep_expired_cache_entries(now)
        if now is not None:
            _last_active_recall_cache_sweep_at = now

    expires_at = _resolve_expires_at_ms_from_duration_ms(ttl_ms, raw_now)
    if expires_at is None:
        _active_recall_cache.pop(cache_key, None)
        return

    if cache_key in _active_recall_cache:
        _active_recall_cache.pop(cache_key, None)

    _active_recall_cache[cache_key] = CachedActiveRecallResult(
        expires_at=expires_at,
        result=result,
    )

    while len(_active_recall_cache) > DEFAULT_MAX_CACHE_ENTRIES:
        oldest_key = next(iter(_active_recall_cache))
        if oldest_key is None:
            break
        _active_recall_cache.pop(oldest_key, None)


def _sweep_expired_cache_entries(now: float | None = None) -> None:
    global _active_recall_cache
    if now is None:
        _active_recall_cache.clear()
        return
    keys_to_delete = []
    for cache_key, cached in _active_recall_cache.items():
        expires_at = _as_date_timestamp_ms(cached.expires_at)
        if expires_at is None or expires_at <= now:
            keys_to_delete.append(cache_key)
    for key in keys_to_delete:
        _active_recall_cache.pop(key, None)


def should_cache_result(result: Any) -> bool:
    if isinstance(result, dict):
        return result.get("status") == "ok" and len(result.get("summary", "") or "") > 0
    return False


def reset_active_recall_cache() -> None:
    global _last_active_recall_cache_sweep_at
    _active_recall_cache.clear()
    _last_active_recall_cache_sweep_at = 0.0