"""Timestamp helpers validate time zones and format log timestamps.

Mirrors src/logging/timestamps.ts.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Literal
import zoneinfo

_valid_time_zone_cache: dict[str, bool] = {}
_timestamp_formatter_cache: dict[str, bool] = {}
_host_time_zone: str | None = None

TimestampStyle = Literal["short", "medium", "long"]


def is_valid_time_zone(tz: str) -> bool:
    cached = _valid_time_zone_cache.get(tz)
    if cached is not None:
        return cached
    try:
        zoneinfo.ZoneInfo(tz)
        valid = True
    except Exception:
        valid = False
    _valid_time_zone_cache[tz] = valid
    return valid


def _resolve_effective_time_zone(time_zone: str | None = None) -> str:
    global _host_time_zone
    explicit = time_zone or os.environ.get("TZ")
    if explicit and is_valid_time_zone(explicit):
        return explicit
    if _host_time_zone is None:
        _host_time_zone = datetime.now().astimezone().tzinfo.key() if datetime.now().astimezone().tzinfo else "UTC"
    return _host_time_zone


def _format_offset(offset_seconds: float) -> str:
    if offset_seconds == 0:
        return "+00:00"
    sign = "+" if offset_seconds > 0 else "-"
    offset = abs(offset_seconds)
    hours = int(offset // 3600)
    minutes = int((offset % 3600) // 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def _get_timestamp_parts(date: datetime, time_zone: str | None = None) -> dict[str, str]:
    effective_tz = _resolve_effective_time_zone(time_zone)
    try:
        tz_info = zoneinfo.ZoneInfo(effective_tz)
    except Exception:
        tz_info = timezone.utc
    localized = date.astimezone(tz_info)
    offset_seconds = localized.utcoffset().total_seconds() if localized.utcoffset() else 0
    return {
        "year": f"{localized.year:04d}",
        "month": f"{localized.month:02d}",
        "day": f"{localized.day:02d}",
        "hour": f"{localized.hour:02d}",
        "minute": f"{localized.minute:02d}",
        "second": f"{localized.second:02d}",
        "fractionalSecond": f"{localized.microsecond // 1000:03d}",
        "offset": _format_offset(offset_seconds),
    }


def format_timestamp(date: datetime, options: dict[str, str] | None = None) -> str:
    style = (options or {}).get("style", "medium")
    parts = _get_timestamp_parts(date, (options or {}).get("timeZone"))
    if style == "short":
        return f"{parts['hour']}:{parts['minute']}:{parts['second']}{parts['offset']}"
    if style == "medium":
        return f"{parts['hour']}:{parts['minute']}:{parts['second']}.{parts['fractionalSecond']}{parts['offset']}"
    if style == "long":
        return f"{parts['year']}-{parts['month']}-{parts['day']}T{parts['hour']}:{parts['minute']}:{parts['second']}.{parts['fractionalSecond']}{parts['offset']}"
    raise ValueError("Unsupported timestamp style")


def format_local_iso_with_offset(now: datetime, time_zone: str | None = None) -> str:
    return format_timestamp(now, {"style": "long", "timeZone": time_zone})


__all__ = [
    "TimestampStyle",
    "is_valid_time_zone",
    "format_timestamp",
    "format_local_iso_with_offset",
]
