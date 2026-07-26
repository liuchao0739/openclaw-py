"""Number coercion utilities.

Mirrors packages/normalization-core/src/number-coercion.ts.
"""

from __future__ import annotations

import math
import re
import time
from typing import Any

MAX_TIMER_TIMEOUT_MS = 2_147_000_000
MAX_TIMER_TIMEOUT_SECONDS = MAX_TIMER_TIMEOUT_MS // 1000
MAX_DATE_TIMESTAMP_MS = 8_640_000_000_000_000
UNIX_EPOCH_ISO_STRING = "1970-01-01T00:00:00.000Z"

_MS_PER_DAY = 86_400_000
_MS_PER_HOUR = 3_600_000
_MS_PER_MINUTE = 60_000
_MS_PER_SECOND = 1_000
_MAX_SAFE_INTEGER = 2**53 - 1
_STRICT_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_STRICT_FINITE_NUMBER_RE = re.compile(
    r"^[+-]?(?:(?:\d+\.?\d*)|(?:\.\d+))(?:e[+-]?\d+)?$",
    re.IGNORECASE,
)


def _modulo(value: int, divisor: int) -> int:
    return value - (value // divisor) * divisor


def _day(timestamp_ms: int) -> int:
    return timestamp_ms // _MS_PER_DAY


def _hour_from_time(timestamp_ms: int) -> int:
    return _modulo(timestamp_ms // _MS_PER_HOUR, 24)


def _minute_from_time(timestamp_ms: int) -> int:
    return _modulo(timestamp_ms // _MS_PER_MINUTE, 60)


def _second_from_time(timestamp_ms: int) -> int:
    return _modulo(timestamp_ms // _MS_PER_SECOND, 60)


def _ms_from_time(timestamp_ms: int) -> int:
    return _modulo(timestamp_ms, _MS_PER_SECOND)


def _day_from_year(year: int) -> int:
    return (
        365 * (year - 1970)
        + (year - 1969) // 4
        - (year - 1901) // 100
        + (year - 1601) // 400
    )


def _time_from_year(year: int) -> int:
    return _day_from_year(year) * _MS_PER_DAY


def _year_from_time(timestamp_ms: int) -> int:
    low = -271_821
    high = 275_760
    while low < high:
        mid = (low + high + 1) // 2
        if _time_from_year(mid) <= timestamp_ms:
            low = mid
        else:
            high = mid - 1
    return low


def _in_leap_year(year: int) -> bool:
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return year % 4 == 0


def _day_within_year(timestamp_ms: int) -> int:
    return _day(timestamp_ms) - _day_from_year(_year_from_time(timestamp_ms))


def _month_from_time(timestamp_ms: int) -> int:
    day_within_year = _day_within_year(timestamp_ms)
    leap = _in_leap_year(_year_from_time(timestamp_ms))
    if day_within_year < 31:
        return 0
    if day_within_year < 59 + leap:
        return 1
    if day_within_year < 90 + leap:
        return 2
    if day_within_year < 120 + leap:
        return 3
    if day_within_year < 151 + leap:
        return 4
    if day_within_year < 181 + leap:
        return 5
    if day_within_year < 212 + leap:
        return 6
    if day_within_year < 243 + leap:
        return 7
    if day_within_year < 273 + leap:
        return 8
    if day_within_year < 304 + leap:
        return 9
    if day_within_year < 334 + leap:
        return 10
    return 11


def _date_from_time(timestamp_ms: int) -> int:
    month = _month_from_time(timestamp_ms)
    day_within_year = _day_within_year(timestamp_ms)
    leap = _in_leap_year(_year_from_time(timestamp_ms))
    offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if leap:
        offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return day_within_year - offsets[month] + 1


def _format_ecma_iso_string(timestamp_ms: int) -> str:
    year = _year_from_time(timestamp_ms)
    month = _month_from_time(timestamp_ms) + 1
    day = _date_from_time(timestamp_ms)
    hours = _hour_from_time(timestamp_ms)
    minutes = _minute_from_time(timestamp_ms)
    seconds = _second_from_time(timestamp_ms)
    millis = _ms_from_time(timestamp_ms)
    if year > 9999:
        year_text = f"+{year:06d}"
    elif year < 0:
        year_text = f"-{abs(year):06d}"
    else:
        year_text = f"{year:04d}"
    return (
        f"{year_text}-{month:02d}-{day:02d}T{hours:02d}:{minutes:02d}:"
        f"{seconds:02d}.{millis:03d}Z"
    )


def _normalize_numeric_string(value: str) -> str | None:
    trimmed = value.strip()
    return trimmed or None


def _is_safe_integer(value: int) -> bool:
    return -_MAX_SAFE_INTEGER - 1 <= value <= _MAX_SAFE_INTEGER


def _coerce_safe_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if _is_safe_integer(value) else None
    if isinstance(value, float) and math.isfinite(value) and value == int(value):
        coerced = int(value)
        return coerced if _is_safe_integer(coerced) else None
    return None


def as_finite_number(value: Any) -> float | None:
    """Return a number only when the input is already finite."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def as_finite_number_in_range(
    value: Any,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    min_exclusive: bool = False,
    max_exclusive: bool = False,
) -> float | None:
    """Return a finite number only when it satisfies the supplied inclusive/exclusive bounds."""
    number = as_finite_number(value)
    if number is None:
        return None
    if min_value is not None:
        if min_exclusive:
            if number <= min_value:
                return None
        elif number < min_value:
            return None
    if max_value is not None:
        if max_exclusive:
            if number >= max_value:
                return None
        elif number > max_value:
            return None
    return number


def as_safe_integer_in_range(
    value: Any,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Return a safe integer only when it satisfies the supplied inclusive bounds."""
    coerced = _coerce_safe_integer(value)
    if coerced is None:
        return None
    if min_value is not None and coerced < min_value:
        return None
    if max_value is not None and coerced > max_value:
        return None
    return coerced


def parse_finite_number(value: Any) -> float | None:
    """Parse finite numbers from number values or strict numeric string tokens."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    return parse_strict_finite_number(value)


def parse_strict_integer(value: Any) -> int | None:
    """Parse only safe integer numbers or base-10 integer strings."""
    coerced = _coerce_safe_integer(value)
    if coerced is not None:
        return coerced
    if not isinstance(value, str):
        return None
    normalized = _normalize_numeric_string(value)
    if not normalized or not _STRICT_INTEGER_RE.fullmatch(normalized):
        return None
    parsed = int(normalized, 10)
    return parsed if _is_safe_integer(parsed) else None


def parse_strict_finite_number(value: Any) -> float | None:
    """Parse only finite decimal/scientific string tokens, rejecting partial numbers."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    normalized = _normalize_numeric_string(value)
    if not normalized or not _STRICT_FINITE_NUMBER_RE.fullmatch(normalized):
        return None
    parsed = float(normalized)
    return parsed if math.isfinite(parsed) else None


def as_positive_safe_integer(value: Any) -> int | None:
    """Return positive safe integers without string coercion."""
    coerced = _coerce_safe_integer(value)
    return coerced if coerced is not None and coerced > 0 else None


def as_date_timestamp_ms(value: Any) -> int | None:
    """Return a Date-valid millisecond timestamp."""
    number = as_finite_number_in_range(
        value,
        min_value=-MAX_DATE_TIMESTAMP_MS,
        max_value=MAX_DATE_TIMESTAMP_MS,
    )
    if number is None:
        return None
    return int(number)


def is_future_date_timestamp_ms(value: Any, *, now_ms: float | None = None) -> bool:
    """Check whether a Date-valid timestamp is after the supplied/current time."""
    timestamp_ms = as_date_timestamp_ms(value)
    resolved_now_ms = as_date_timestamp_ms(now_ms if now_ms is not None else time.time() * 1000)
    return (
        timestamp_ms is not None
        and resolved_now_ms is not None
        and timestamp_ms > resolved_now_ms
    )


def timestamp_ms_to_iso_string(value: Any) -> str | None:
    """Convert Date-valid millisecond timestamps to ISO strings."""
    timestamp_ms = as_date_timestamp_ms(value)
    if timestamp_ms is None:
        return None
    try:
        return _format_ecma_iso_string(timestamp_ms)
    except (OverflowError, ValueError):
        return None


def resolve_date_timestamp_ms(value: Any, fallback_value: Any = None) -> int:
    """Resolve a Date-valid timestamp with a Date-valid fallback."""
    if fallback_value is None:
        fallback_value = time.time() * 1000
    return as_date_timestamp_ms(value) or as_date_timestamp_ms(fallback_value) or 0


def resolve_timestamp_ms_to_iso_string(value: Any, fallback_value: Any = None) -> str:
    """Resolve a Date-valid timestamp to ISO, falling back to Unix epoch if needed."""
    if fallback_value is None:
        fallback_value = time.time() * 1000
    return (
        timestamp_ms_to_iso_string(value)
        or timestamp_ms_to_iso_string(fallback_value)
        or UNIX_EPOCH_ISO_STRING
    )


def timestamp_ms_to_iso_file_stamp(value: Any, fallback_value: Any = None) -> str:
    """Format Date-valid timestamps for filenames by replacing colon separators."""
    if fallback_value is None:
        fallback_value = time.time() * 1000
    return resolve_timestamp_ms_to_iso_string(value, fallback_value).replace(":", "-")


def clamp_timer_timeout_ms(value_ms: Any, min_ms: int = 1) -> int | None:
    """Clamp finite millisecond values into the Node-safe timer range."""
    value = as_finite_number(value_ms)
    if value is None:
        return None
    minimum = max(1, math.floor(min_ms))
    return int(min(max(math.floor(value), minimum), MAX_TIMER_TIMEOUT_MS))


def clamp_positive_timer_timeout_ms(value_ms: Any) -> int | None:
    """Clamp positive finite millisecond values into the Node-safe timer range."""
    value = as_finite_number(value_ms)
    if value is None or value <= 0:
        return None
    return clamp_timer_timeout_ms(value)


def resolve_positive_timer_timeout_ms(value_ms: Any, fallback_ms: float) -> int:
    """Resolve a positive timer timeout or fall back through safe timer clamping."""
    return clamp_positive_timer_timeout_ms(value_ms) or resolve_timer_timeout_ms(fallback_ms, 1)


def resolve_timer_timeout_ms(value_ms: Any, fallback_ms: float, min_ms: int = 1) -> int:
    """Resolve arbitrary timeout input with fallback and minimum timer bounds."""
    value = as_finite_number(value_ms) or as_finite_number(fallback_ms)
    minimum = max(0, math.floor(min_ms))
    if value is None:
        return int(minimum)
    return int(min(max(math.floor(value), minimum), MAX_TIMER_TIMEOUT_MS))


def add_timer_timeout_grace_ms(timeout_ms: Any, grace_ms: float = 5_000) -> int | None:
    """Add grace time to a finite timeout and clamp the result to Node-safe bounds."""
    timeout = as_finite_number(timeout_ms)
    grace = as_finite_number(grace_ms)
    if timeout is None or grace is None:
        return None
    with_grace = timeout + grace
    if not math.isfinite(with_grace):
        return MAX_TIMER_TIMEOUT_MS
    return clamp_timer_timeout_ms(with_grace)


def finite_seconds_to_timer_safe_milliseconds(
    value: Any,
    *,
    floor_seconds: bool = False,
) -> int | None:
    """Convert finite positive seconds to Node-safe milliseconds."""
    seconds = as_finite_number(value)
    if seconds is None or seconds <= 0:
        return None
    bounded_seconds = math.floor(seconds) if floor_seconds else seconds
    milliseconds = math.floor(bounded_seconds * 1000)
    if not math.isfinite(milliseconds) or milliseconds <= 0:
        return None
    return int(min(milliseconds, MAX_TIMER_TIMEOUT_MS))


def resolve_integer_option(
    value: Any,
    fallback: float,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Resolve an integer option from finite numeric input or fallback, then clamp bounds."""
    candidate = (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        else fallback
    )
    floored = math.floor(candidate)
    min_bounded = max(min_value, floored) if min_value is not None else floored
    return int(min(max_value, min_bounded) if max_value is not None else min_bounded)


def resolve_optional_integer_option(
    value: Any,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    """Resolve an optional integer option, returning None for non-finite input."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    return resolve_integer_option(value, value, min_value=min_value, max_value=max_value)


def resolve_non_negative_integer_option(value: Any, fallback: float) -> int:
    """Resolve an integer option with a non-negative lower bound."""
    return resolve_integer_option(value, fallback, min_value=0)


def parse_strict_positive_integer(value: Any) -> int | None:
    """Parse strict positive integer values from numbers or strings."""
    parsed = parse_strict_integer(value)
    return parsed if parsed is not None and parsed > 0 else None


def parse_strict_non_negative_integer(value: Any) -> int | None:
    """Parse strict non-negative integer values from numbers or strings."""
    parsed = parse_strict_integer(value)
    return parsed if parsed is not None and parsed >= 0 else None


def positive_seconds_to_safe_milliseconds(value: Any) -> int | None:
    """Convert strict positive seconds to safe millisecond counts."""
    seconds = parse_strict_positive_integer(value)
    if seconds is None:
        return None
    milliseconds = seconds * 1000
    return milliseconds if _is_safe_integer(milliseconds) else None


def non_negative_seconds_to_safe_milliseconds(value: Any) -> int | None:
    """Convert strict non-negative seconds to safe millisecond counts."""
    seconds = parse_strict_non_negative_integer(value)
    if seconds is None:
        return None
    milliseconds = seconds * 1000
    return milliseconds if _is_safe_integer(milliseconds) else None


def resolve_expires_at_ms_from_duration_ms(
    value: Any,
    *,
    now_ms: float | None = None,
    buffer_ms: float = 0,
    min_remaining_ms: int | None = None,
) -> int | None:
    """Resolve an absolute expiration timestamp from a positive duration in milliseconds."""
    duration_ms = as_positive_safe_integer(value)
    if duration_ms is None:
        return None
    resolved_now_ms = as_date_timestamp_ms(now_ms if now_ms is not None else time.time() * 1000)
    resolved_buffer_ms = as_finite_number(buffer_ms)
    if resolved_now_ms is None or resolved_buffer_ms is None:
        return None
    expires_at = resolved_now_ms + duration_ms - int(resolved_buffer_ms)
    if not _is_safe_integer(expires_at) or timestamp_ms_to_iso_string(expires_at) is None:
        return None
    if min_remaining_ms is None:
        return expires_at
    min_expires_at = resolved_now_ms + min_remaining_ms
    if not _is_safe_integer(min_expires_at) or timestamp_ms_to_iso_string(min_expires_at) is None:
        return expires_at
    return max(expires_at, min_expires_at)


def resolve_expires_at_ms_from_duration_seconds(
    value: Any,
    *,
    now_ms: float | None = None,
    buffer_ms: float = 0,
    min_remaining_ms: int | None = None,
) -> int | None:
    """Resolve an absolute expiration timestamp from a positive duration in seconds."""
    duration_ms = positive_seconds_to_safe_milliseconds(value)
    if duration_ms is None:
        return None
    return resolve_expires_at_ms_from_duration_ms(
        duration_ms,
        now_ms=now_ms,
        buffer_ms=buffer_ms,
        min_remaining_ms=min_remaining_ms,
    )


def resolve_expires_at_ms_from_epoch_seconds(
    value: Any,
    *,
    buffer_ms: float = 0,
    max_ms: int | None = None,
) -> int | None:
    """Resolve an absolute expiration timestamp from Unix epoch seconds."""
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    ):
        epoch_ms = math.trunc(value) * 1000
    else:
        epoch_ms = positive_seconds_to_safe_milliseconds(value)
    if epoch_ms is None:
        return None
    expires_at = epoch_ms - int(buffer_ms)
    if not _is_safe_integer(expires_at):
        return None
    if timestamp_ms_to_iso_string(expires_at) is None:
        return None
    return expires_at if max_ms is None or expires_at <= max_ms else None


def resolve_expires_at_ms_from_duration_or_epoch(
    value: Any,
    *,
    now_ms: float | None = None,
    relative_seconds_threshold: int = 1_000_000_000,
    absolute_milliseconds_threshold: int = 1_000_000_000_000,
) -> int | None:
    """Resolve expiration input that may be relative seconds, epoch seconds, or epoch milliseconds."""
    parsed = parse_strict_positive_integer(value)
    if parsed is None:
        return None
    if parsed < relative_seconds_threshold:
        return resolve_expires_at_ms_from_duration_seconds(parsed, now_ms=now_ms)
    if parsed < absolute_milliseconds_threshold:
        return resolve_expires_at_ms_from_epoch_seconds(parsed)
    return as_date_timestamp_ms(parsed)


__all__ = [
    "MAX_DATE_TIMESTAMP_MS",
    "MAX_TIMER_TIMEOUT_MS",
    "MAX_TIMER_TIMEOUT_SECONDS",
    "UNIX_EPOCH_ISO_STRING",
    "add_timer_timeout_grace_ms",
    "as_date_timestamp_ms",
    "as_finite_number",
    "as_finite_number_in_range",
    "as_positive_safe_integer",
    "as_safe_integer_in_range",
    "clamp_positive_timer_timeout_ms",
    "clamp_timer_timeout_ms",
    "finite_seconds_to_timer_safe_milliseconds",
    "is_future_date_timestamp_ms",
    "non_negative_seconds_to_safe_milliseconds",
    "parse_finite_number",
    "parse_strict_finite_number",
    "parse_strict_integer",
    "parse_strict_non_negative_integer",
    "parse_strict_positive_integer",
    "positive_seconds_to_safe_milliseconds",
    "resolve_date_timestamp_ms",
    "resolve_expires_at_ms_from_duration_ms",
    "resolve_expires_at_ms_from_duration_or_epoch",
    "resolve_expires_at_ms_from_duration_seconds",
    "resolve_expires_at_ms_from_epoch_seconds",
    "resolve_integer_option",
    "resolve_non_negative_integer_option",
    "resolve_optional_integer_option",
    "resolve_positive_timer_timeout_ms",
    "resolve_timer_timeout_ms",
    "resolve_timestamp_ms_to_iso_string",
    "timestamp_ms_to_iso_file_stamp",
    "timestamp_ms_to_iso_string",
]
