"""Relative time formatting helpers.

Mirrors src/infra/format-time/format-relative.ts.
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime
from typing import Any, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openclaw.infra.format_time.format_datetime import resolve_timezone


class FormatTimeAgoOptions(TypedDict, total=False):
    suffix: bool
    fallback: str


class FormatRelativeTimestampOptions(TypedDict, total=False):
    date_fallback: bool
    timezone: str
    fallback: str


def _js_round(value: float) -> int:
    """Round like JavaScript Math.round for non-negative values."""
    return int(value + 0.5)


def _is_finite(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (math.isnan(value) or math.isinf(value))
    return False


def _now_ms() -> float:
    return time.time() * 1000


def format_time_ago(
    duration_ms: float | None,
    options: FormatTimeAgoOptions | None = None,
) -> str:
    """Format a duration (in ms) as a human-readable relative time."""
    opts = options or {}
    suffix = opts.get("suffix", True)
    fallback = opts.get("fallback", "unknown")

    if duration_ms is None or not _is_finite(duration_ms) or duration_ms < 0:
        return fallback

    total_seconds = _js_round(duration_ms / 1000)
    minutes = _js_round(total_seconds / 60)

    if minutes < 1:
        return "just now" if suffix else f"{total_seconds}s"
    if minutes < 60:
        return f"{minutes}m ago" if suffix else f"{minutes}m"
    hours = _js_round(minutes / 60)
    if hours < 48:
        return f"{hours}h ago" if suffix else f"{hours}h"
    days = _js_round(hours / 24)
    return f"{days}d ago" if suffix else f"{days}d"


def format_relative_timestamp(
    timestamp_ms: float | None,
    options: FormatRelativeTimestampOptions | None = None,
) -> str:
    """Format an epoch timestamp relative to now."""
    opts = options or {}
    fallback = opts.get("fallback", "n/a")
    if timestamp_ms is None or not _is_finite(timestamp_ms):
        return fallback

    diff = _now_ms() - timestamp_ms
    abs_diff = abs(diff)
    is_past = diff >= 0

    sec = _js_round(abs_diff / 1000)
    if sec < 60:
        return "just now" if is_past else "in <1m"

    minute = _js_round(sec / 60)
    if minute < 60:
        return f"{minute}m ago" if is_past else f"in {minute}m"

    hr = _js_round(minute / 60)
    if hr < 48:
        return f"{hr}h ago" if is_past else f"in {hr}h"

    day = _js_round(hr / 24)
    if not opts.get("date_fallback") or day <= 7:
        return f"{day}d ago" if is_past else f"in {day}d"

    try:
        tz_name = opts.get("timezone")
        if tz_name is not None and resolve_timezone(tz_name) is None:
            raise ValueError("invalid timezone")
        tz = ZoneInfo(tz_name) if tz_name else UTC
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).astimezone(tz)
        return f"{dt.strftime('%b')} {dt.day}"
    except (ZoneInfoNotFoundError, ValueError, OSError, OverflowError):
        return f"{day}d ago"
