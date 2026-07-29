from __future__ import annotations

import re

_DURATION_UNITS: dict[str, int] = {
    "ms": 1,
    "s": 1000,
    "sec": 1000,
    "second": 1000,
    "seconds": 1000,
    "m": 60 * 1000,
    "min": 60 * 1000,
    "minute": 60 * 1000,
    "minutes": 60 * 1000,
    "h": 60 * 60 * 1000,
    "hr": 60 * 60 * 1000,
    "hour": 60 * 60 * 1000,
    "hours": 60 * 60 * 1000,
    "d": 24 * 60 * 60 * 1000,
    "day": 24 * 60 * 60 * 1000,
    "days": 24 * 60 * 60 * 1000,
}

_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([a-z]+)?$", re.IGNORECASE)


def parse_duration_to_ms(raw: str) -> int | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if trimmed.isdigit():
        return int(trimmed)
    m = _DURATION_RE.match(trimmed)
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "ms").lower()
    multiplier = _DURATION_UNITS.get(unit)
    if multiplier is None:
        return None
    return int(value * multiplier)
