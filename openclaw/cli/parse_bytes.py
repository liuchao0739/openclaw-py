from __future__ import annotations

import re

from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

UNIT_MULTIPLIERS = {
    "b": 1,
    "kb": 1024,
    "k": 1024,
    "mb": 1024**2,
    "m": 1024**2,
    "gb": 1024**3,
    "g": 1024**3,
    "tb": 1024**4,
    "t": 1024**4,
}

_BYTE_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)([a-z]+)?$")


def _invalid_byte_size(raw: str, reason: str | None = None) -> Exception:
    value = f'"{raw}"' if raw.strip() else "empty value"
    prefix = f"Invalid byte size ({reason}): {value}." if reason else f"Invalid byte size: {value}."
    return ValueError(f"{prefix} Use values like 512kb, 10mb, 1gb, or 500.")


def parse_byte_size(raw: str, opts: dict | None = None) -> int:
    options = opts or {}
    trimmed = normalize_lowercase_string_or_empty(normalize_optional_string(raw) or "")
    if not trimmed:
        raise _invalid_byte_size(raw, "empty")
    m = _BYTE_SIZE_RE.match(trimmed)
    if not m:
        raise _invalid_byte_size(raw)
    value = float(m.group(1))
    if not (value == value and value != float("inf") and value != float("-inf")) or value < 0:
        raise _invalid_byte_size(raw)
    unit = normalize_lowercase_string_or_empty(m.group(2) or options.get("defaultUnit", "b"))
    multiplier = UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        raise _invalid_byte_size(raw, f'unknown unit "{unit}"')
    import math

    bytes_value = round(value * multiplier)
    if not math.isfinite(bytes_value):
        raise _invalid_byte_size(raw)
    return bytes_value
