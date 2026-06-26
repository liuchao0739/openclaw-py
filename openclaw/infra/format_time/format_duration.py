"""Duration formatting helpers produce compact, precise, and human display
strings from millisecond values.

Mirrors src/infra/format-time/format-duration.ts.
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal


def _is_finite(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (math.isnan(value) or math.isinf(value))
    return False


def format_duration_seconds(
    ms: float,
    options: dict[str, Any] | None = None,
) -> str:
    """Format milliseconds as seconds with optional decimals."""
    if not _is_finite(ms):
        return "unknown"
    opts = options or {}
    decimals = opts.get("decimals", 1)
    unit = opts.get("unit", "s")
    seconds = max(0, ms) / 1000
    fixed = f"{seconds:.{max(0, int(decimals))}f}"
    # Trim trailing zeros: "1.0" -> "1", "1.50" -> "1.5"
    trimmed = re.sub(r"\.0+$", "", fixed)
    trimmed = re.sub(r"(\.\d*[1-9])0+$", r"\1", trimmed)
    return f"{trimmed} seconds" if unit == "seconds" else f"{trimmed}s"


def format_duration_precise(
    ms: float,
    options: dict[str, Any] | None = None,
) -> str:
    """Precise decimal-seconds output: '500ms' or '1.23s'."""
    if not _is_finite(ms):
        return "unknown"
    if ms < 1000:
        return f"{max(0, round(ms))}ms"
    opts = options or {}
    return format_duration_seconds(
        ms,
        {"decimals": opts.get("decimals", 2), "unit": opts.get("unit", "s")},
    )


def format_duration_compact(
    ms: float | None,
    options: dict[str, Any] | None = None,
) -> str | None:
    """Compact compound duration: '500ms', '45s', '2m5s', '1h30m'.

    With ``spaced``: '45s', '2m 5s', '1h 30m'.
    Omits trailing zero components. Returns None for null/non-finite/non-positive.
    """
    if ms is None or not _is_finite(ms) or ms <= 0:
        return None
    if ms < 1000:
        return f"{round(ms)}ms"
    opts = options or {}
    sep = " " if opts.get("spaced") else ""
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
    ms: float | None,
    fallback: str = "n/a",
) -> str:
    """Rounded single-unit duration for display: '500ms', '5s', '3m', '2h', '5d'."""
    if ms is None or not _is_finite(ms) or ms < 0:
        return fallback
    if ms < 1000:
        return f"{round(ms)}ms"
    sec = round(ms / 1000)
    if sec < 60:
        return f"{sec}s"
    minute = round(sec / 60)
    if minute < 60:
        return f"{minute}m"
    hr = round(minute / 60)
    if hr < 24:
        return f"{hr}h"
    day = round(hr / 24)
    return f"{day}d"
