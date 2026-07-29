"""Diagnostic memory helpers capture process memory facts for support diagnostics.

Mirrors src/logging/diagnostic-memory.ts.
"""

from __future__ import annotations

import os
import time
from typing import Any

_MB = 1024 * 1024
DEFAULT_RSS_WARNING_BYTES = 1536 * _MB
DEFAULT_RSS_CRITICAL_BYTES = 3072 * _MB
DEFAULT_HEAP_WARNING_BYTES = 1024 * _MB
DEFAULT_HEAP_CRITICAL_BYTES = 2048 * _MB
DEFAULT_RSS_GROWTH_WARNING_BYTES = 512 * _MB
DEFAULT_RSS_GROWTH_CRITICAL_BYTES = 1024 * _MB
DEFAULT_GROWTH_WINDOW_MS = 10 * 60 * 1000
DEFAULT_PRESSURE_REPEAT_MS = 5 * 60 * 1000

_state: dict[str, Any] = {
    "lastSample": None,
    "lastPressureAtByKey": {},
}


def _normalize_memory_usage() -> dict[str, int]:
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    except Exception:
        rss = 0
    import gc
    gc.collect()
    return {
        "rssBytes": rss,
        "heapTotalBytes": 0,
        "heapUsedBytes": 0,
        "externalBytes": 0,
        "arrayBuffersBytes": 0,
    }


def _resolve_thresholds(thresholds: dict[str, int] | None = None) -> dict[str, int]:
    t = thresholds or {}
    return {
        "rssWarningBytes": t.get("rssWarningBytes", DEFAULT_RSS_WARNING_BYTES),
        "rssCriticalBytes": t.get("rssCriticalBytes", DEFAULT_RSS_CRITICAL_BYTES),
        "heapUsedWarningBytes": t.get("heapUsedWarningBytes", DEFAULT_HEAP_WARNING_BYTES),
        "heapUsedCriticalBytes": t.get("heapUsedCriticalBytes", DEFAULT_HEAP_CRITICAL_BYTES),
        "rssGrowthWarningBytes": t.get("rssGrowthWarningBytes", DEFAULT_RSS_GROWTH_WARNING_BYTES),
        "rssGrowthCriticalBytes": t.get("rssGrowthCriticalBytes", DEFAULT_RSS_GROWTH_CRITICAL_BYTES),
        "growthWindowMs": t.get("growthWindowMs", DEFAULT_GROWTH_WINDOW_MS),
        "pressureRepeatMs": t.get("pressureRepeatMs", DEFAULT_PRESSURE_REPEAT_MS),
    }


def _pick_threshold_pressure(
    memory: dict[str, int], thresholds: dict[str, int]
) -> dict[str, Any] | None:
    if memory["rssBytes"] >= thresholds["rssCriticalBytes"]:
        return {"level": "critical", "reason": "rss_threshold", "memory": memory, "thresholdBytes": thresholds["rssCriticalBytes"]}
    if memory["heapUsedBytes"] >= thresholds["heapUsedCriticalBytes"]:
        return {"level": "critical", "reason": "heap_threshold", "memory": memory, "thresholdBytes": thresholds["heapUsedCriticalBytes"]}
    if memory["rssBytes"] >= thresholds["rssWarningBytes"]:
        return {"level": "warning", "reason": "rss_threshold", "memory": memory, "thresholdBytes": thresholds["rssWarningBytes"]}
    if memory["heapUsedBytes"] >= thresholds["heapUsedWarningBytes"]:
        return {"level": "warning", "reason": "heap_threshold", "memory": memory, "thresholdBytes": thresholds["heapUsedWarningBytes"]}
    return None


def _pick_growth_pressure(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    thresholds: dict[str, int],
) -> dict[str, Any] | None:
    if not previous:
        return None
    window_ms = current["ts"] - previous["ts"]
    if window_ms <= 0 or window_ms > thresholds["growthWindowMs"]:
        return None
    rss_growth = current["memory"]["rssBytes"] - previous["memory"]["rssBytes"]
    if rss_growth >= thresholds["rssGrowthCriticalBytes"]:
        return {"level": "critical", "reason": "rss_growth", "memory": current["memory"], "thresholdBytes": thresholds["rssGrowthCriticalBytes"], "rssGrowthBytes": rss_growth, "windowMs": window_ms}
    if rss_growth >= thresholds["rssGrowthWarningBytes"]:
        return {"level": "warning", "reason": "rss_growth", "memory": current["memory"], "thresholdBytes": thresholds["rssGrowthWarningBytes"], "rssGrowthBytes": rss_growth, "windowMs": window_ms}
    return None


def _should_emit_pressure(pressure: dict[str, Any], now: int, repeat_ms: int) -> bool:
    key = f"{pressure['level']}:{pressure['reason']}"
    last_at = _state["lastPressureAtByKey"].get(key)
    if last_at is not None and now - last_at < repeat_ms:
        return False
    _state["lastPressureAtByKey"][key] = now
    return True


def emit_diagnostic_memory_sample(options: dict[str, Any] | None = None) -> dict[str, int]:
    now = (options or {}).get("now") or int(time.time() * 1000)
    memory = _normalize_memory_usage()
    current = {"ts": now, "memory": memory}
    thresholds = _resolve_thresholds((options or {}).get("thresholds"))
    pressure = _pick_threshold_pressure(memory, thresholds) or _pick_growth_pressure(_state["lastSample"], current, thresholds)
    _state["lastSample"] = current
    if pressure and _should_emit_pressure(pressure, now, thresholds["pressureRepeatMs"]):
        pass
    return memory


def reset_diagnostic_memory_for_test() -> None:
    _state["lastSample"] = None
    _state["lastPressureAtByKey"].clear()


__all__ = [
    "emit_diagnostic_memory_sample",
    "reset_diagnostic_memory_for_test",
]
