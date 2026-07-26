"""Date/time formatting helpers.

Mirrors src/infra/format-time/format-datetime.ts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class FormatTimestampOptions(TypedDict, total=False):
    display_seconds: bool


class FormatZonedTimestampOptions(FormatTimestampOptions, total=False):
    time_zone: str


def resolve_timezone(value: str) -> str | None:
    """Validate an IANA timezone string. Returns the string if valid, None otherwise."""
    if not value:
        return None
    try:
        ZoneInfo(value)
        return value
    except ZoneInfoNotFoundError:
        return None


def format_utc_timestamp(
    date: datetime,
    options: FormatTimestampOptions | None = None,
) -> str:
    """Format a datetime as a UTC timestamp string."""
    opts = options or {}
    utc = date.astimezone(UTC) if date.tzinfo is not None else date.replace(tzinfo=UTC)
    yyyy = f"{utc.year:04d}"
    mm = f"{utc.month:02d}"
    dd = f"{utc.day:02d}"
    hh = f"{utc.hour:02d}"
    minute = f"{utc.minute:02d}"
    if not opts.get("display_seconds"):
        return f"{yyyy}-{mm}-{dd}T{hh}:{minute}Z"
    sec = f"{utc.second:02d}"
    return f"{yyyy}-{mm}-{dd}T{hh}:{minute}:{sec}Z"


def _get_zoned_format_parts(
    date: datetime,
    time_zone: str | None,
    display_seconds: bool,
) -> dict[str, str | None]:
    """Return Intl-like date/time parts for zoned timestamp formatting."""
    tz = ZoneInfo(time_zone) if time_zone else None
    local = date.astimezone(tz) if tz is not None else date.astimezone()
    parts: dict[str, str | None] = {
        "year": f"{local.year:04d}",
        "month": f"{local.month:02d}",
        "day": f"{local.day:02d}",
        "hour": f"{local.hour:02d}",
        "minute": f"{local.minute:02d}",
        "second": f"{local.second:02d}" if display_seconds else None,
        "timeZoneName": local.tzname(),
    }
    return parts


def format_zoned_timestamp(
    date: datetime,
    options: FormatZonedTimestampOptions | None = None,
) -> str | None:
    """Format a datetime with timezone display. Returns None if formatting fails."""
    opts: dict[str, Any] = dict(options or {})
    display_seconds = bool(opts.get("display_seconds"))
    time_zone = opts.get("time_zone")
    if time_zone is not None and resolve_timezone(time_zone) is None:
        return None
    try:
        if date.tzinfo is None:
            aware = date.replace(tzinfo=UTC)
        else:
            aware = date
        parts = _get_zoned_format_parts(aware, time_zone, display_seconds)
        yyyy = parts.get("year")
        mm = parts.get("month")
        dd = parts.get("day")
        hh = parts.get("hour")
        minute = parts.get("minute")
        sec = parts.get("second") if display_seconds else None
        tz = (parts.get("timeZoneName") or "").strip() or None
        if not yyyy or not mm or not dd or not hh or not minute:
            return None
        if display_seconds and sec:
            return f"{yyyy}-{mm}-{dd} {hh}:{minute}:{sec}{f' {tz}' if tz else ''}"
        return f"{yyyy}-{mm}-{dd} {hh}:{minute}{f' {tz}' if tz else ''}"
    except (ZoneInfoNotFoundError, ValueError, OSError, OverflowError, RuntimeError):
        return None
