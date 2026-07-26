"""Offsetless zoned datetime parsing.

Mirrors src/infra/format-time/parse-offsetless-zoned-datetime.ts.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OFFSETLESS_ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?$")
OFFSETLESS_ISO_DATETIME_PARTS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?$"
)


@dataclass(frozen=True)
class _OffsetlessIsoDateTimeParts:
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    millisecond: int


def is_offsetless_iso_date_time(raw: str) -> bool:
    return OFFSETLESS_ISO_DATETIME_RE.match(raw) is not None


def parse_offsetless_iso_date_time_in_time_zone(raw: str, time_zone: str) -> str | None:
    expected_parts = _parse_offsetless_iso_date_time_parts(raw)
    if expected_parts is None:
        return None
    try:
        _get_zoned_date_time_parts(datetime.now(tz=UTC).timestamp() * 1000, time_zone)

        naive = datetime.fromisoformat(f"{raw}Z")
        naive_ms = naive.timestamp() * 1000
        if not _is_finite_number(naive_ms):
            return None

        first_offset_ms = _get_time_zone_offset_ms(naive_ms, time_zone)
        candidate_ms = naive_ms - first_offset_ms
        final_offset_ms = _get_time_zone_offset_ms(candidate_ms, time_zone)
        resolved_ms = naive_ms - final_offset_ms
        if not _matches_offsetless_iso_date_time_parts(resolved_ms, time_zone, expected_parts):
            return None
        resolved = datetime.fromtimestamp(resolved_ms / 1000, tz=UTC)
        return _to_utc_iso_string(resolved)
    except (ZoneInfoNotFoundError, ValueError, OSError, OverflowError):
        return None


def _to_utc_iso_string(date: datetime) -> str:
    utc = date.astimezone(UTC)
    millis = utc.microsecond // 1000
    return f"{utc.strftime('%Y-%m-%dT%H:%M:%S')}.{millis:03d}Z"


def _is_finite_number(value: float) -> bool:
    return math.isfinite(value)


def _parse_offsetless_iso_date_time_parts(raw: str) -> _OffsetlessIsoDateTimeParts | None:
    match = OFFSETLESS_ISO_DATETIME_PARTS_RE.match(raw)
    if not match:
        return None
    fractional_ms = (match.group(7) or "").ljust(3, "0")[:3]
    return _OffsetlessIsoDateTimeParts(
        year=int(match.group(1) or "0"),
        month=int(match.group(2) or "0"),
        day=int(match.group(3) or "0"),
        hour=int(match.group(4) or "0"),
        minute=int(match.group(5) or "0"),
        second=int(match.group(6) or "0"),
        millisecond=int(fractional_ms or "0"),
    )


def _matches_offsetless_iso_date_time_parts(
    utc_ms: float,
    time_zone: str,
    expected: _OffsetlessIsoDateTimeParts,
) -> bool:
    actual = _get_zoned_date_time_parts(utc_ms, time_zone)
    return (
        actual.year == expected.year
        and actual.month == expected.month
        and actual.day == expected.day
        and actual.hour == expected.hour
        and actual.minute == expected.minute
        and actual.second == expected.second
        and actual.millisecond == expected.millisecond
    )


def _get_time_zone_offset_ms(utc_ms: float, time_zone: str) -> float:
    parts = _get_zoned_date_time_parts(utc_ms, time_zone)
    local_as_utc = (
        datetime(
            parts.year,
            parts.month,
            parts.day,
            parts.hour,
            parts.minute,
            parts.second,
            parts.millisecond * 1000,
            tzinfo=UTC,
        ).timestamp()
        * 1000
    )
    return local_as_utc - utc_ms


def _get_zoned_date_time_parts(utc_ms: float, time_zone: str) -> _OffsetlessIsoDateTimeParts:
    utc_date = datetime.fromtimestamp(utc_ms / 1000, tz=UTC)
    local = utc_date.astimezone(ZoneInfo(time_zone))
    millisecond = utc_date.microsecond // 1000
    return _OffsetlessIsoDateTimeParts(
        year=local.year,
        month=local.month,
        day=local.day,
        hour=local.hour,
        minute=local.minute,
        second=local.second,
        millisecond=millisecond,
    )
