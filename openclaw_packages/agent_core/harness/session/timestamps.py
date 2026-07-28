from __future__ import annotations

import re
import time


def parse_session_timestamp_ms(value: str | int | float | None) -> int | None:
    if not isinstance(value, (str, int, float)):
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            parsed = _parse_iso_timestamp(trimmed)
            return parsed
        except (ValueError, OverflowError):
            return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _parse_iso_timestamp(value: str) -> int | None:
    try:
        from datetime import datetime, timezone
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, OverflowError):
        return None


def require_session_timestamp_ms(value: str, label: str) -> int:
    parsed = parse_session_timestamp_ms(value)
    if parsed is None:
        raise Exception(f"{label} must be a valid timestamp")
    return parsed
