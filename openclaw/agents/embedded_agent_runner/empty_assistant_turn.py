"""Detects provider stop turns with no assistant-visible content."""

from __future__ import annotations

from typing import Any


def _read_finite(value: object) -> float | None:
    if not isinstance(value, (int, float)) or value != value:
        return None
    return float(value)


def _has_zero_token_usage_snapshot(usage: object) -> bool:
    if not usage or not isinstance(usage, dict):
        return False
    inp = _read_finite(usage.get("input"))
    out = _read_finite(usage.get("output"))
    cache_read = _read_finite(usage.get("cacheRead"))
    cache_write = _read_finite(usage.get("cacheWrite"))
    total = _read_finite(
        usage.get("total") or usage.get("totalTokens") or usage.get("total_tokens")
    )
    if total is not None:
        return total == 0 and all(
            v is None or v == 0 for v in (inp, out, cache_read, cache_write)
        )
    components = [v for v in (inp, out, cache_read, cache_write) if v is not None]
    return len(components) > 0 and all(v == 0 for v in components)


def is_zero_usage_empty_stop_assistant_turn(message: dict[str, Any] | None) -> bool:
    if not message:
        return False
    return bool(
        message.get("stopReason") == "stop"
        and isinstance(message.get("content"), list)
        and len(message["content"]) == 0
        and _has_zero_token_usage_snapshot(message.get("usage"))
    )