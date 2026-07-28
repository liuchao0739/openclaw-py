from __future__ import annotations

import math
from typing import Any, Optional


def _is_finite(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (math.isnan(value) or math.isinf(value))
    return False


def format_duration_seconds(
    ms: int | float,
    options: dict[str, Any] | None = None,
) -> str:
    if not _is_finite(ms):
        return "unknown"
    opts = options or {}
    decimals = opts.get("decimals", 1)
    unit = opts.get("unit", "s")
    seconds = max(0, ms) / 1000
    fixed = f"{seconds:.{max(0, decimals)}f}"
    if "." in fixed:
        trimmed = fixed.rstrip("0").rstrip(".")
    else:
        trimmed = fixed
    return f"{trimmed} seconds" if unit == "seconds" else f"{trimmed}s"


def format_duration_precise(
    ms: int | float,
    options: dict[str, Any] | None = None,
) -> str:
    if not _is_finite(ms):
        return "unknown"
    if ms < 1000:
        return f"{max(0, round(ms))}ms"
    opts = options or {}
    decimals = opts.get("decimals", 2)
    unit = opts.get("unit", "s")
    return format_duration_seconds(ms, {"decimals": decimals, "unit": unit})


def format_duration_compact(
    ms: int | float | None = None,
    options: dict[str, Any] | None = None,
) -> str | None:
    if ms is None or not _is_finite(ms) or ms <= 0:
        return None
    if ms < 1000:
        return f"{round(ms)}ms"
    opts = options or {}
    spaced = opts.get("spaced", False)
    sep = " " if spaced else ""
    total_seconds = round(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours >= 24:
        days = hours // 24
        remaining_hours = hours % 24
        return f"{days}d{sep}{remaining_hours}h" if remaining_hours > 0 else f"{days}d"
    if hours > 0:
        return f"{hours}h{sep}{minutes}m" if minutes > 0 else f"{hours}h"
    if minutes > 0:
        return f"{minutes}m{sep}{seconds}s" if seconds > 0 else f"{minutes}m"
    return f"{seconds}s"


def format_duration_human(
    ms: int | float | None = None,
    fallback: str = "n/a",
) -> str:
    if ms is None or not _is_finite(ms) or ms < 0:
        return fallback
    if ms < 1000:
        return f"{round(ms)}ms"
    sec = round(ms / 1000)
    if sec < 60:
        return f"{sec}s"
    min = round(sec / 60)
    if min < 60:
        return f"{min}m"
    hr = round(min / 60)
    if hr < 24:
        return f"{hr}h"
    day = round(hr / 24)
    return f"{day}d"


def format_duration(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def format_datetime(ts: float, *, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(fmt)


def format_relative(ts: float, now: float | None = None) -> str:
    import time
    if now is None:
        now = time.time()
    diff = now - ts
    if abs(diff) < 60:
        return "just now"
    if abs(diff) < 3600:
        minutes = int(abs(diff) / 60)
        return f"{minutes}m ago" if diff > 0 else f"in {minutes}m"
    if abs(diff) < 86400:
        hours = int(abs(diff) / 3600)
        return f"{hours}h ago" if diff > 0 else f"in {hours}h"
    days = int(abs(diff) / 86400)
    return f"{days}d ago" if diff > 0 else f"in {days}d"
