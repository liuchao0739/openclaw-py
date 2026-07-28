from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def normalize_optional_lowercase_string(value: Any) -> str | None:
    result = normalize_optional_string(value)
    return result.lower() if result else None


def normalize_lowercase_string_or_empty(value: Any) -> str:
    result = normalize_optional_lowercase_string(value)
    return result or ""


def resolve_integer_option(
    value: Any,
    fallback: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    if isinstance(value, bool):
        candidate = fallback
    elif isinstance(value, (int, float)) and math.isfinite(value):
        candidate = math.floor(float(value))
    else:
        candidate = fallback
    if min_value is not None:
        candidate = max(min_value, candidate)
    if max_value is not None:
        candidate = min(max_value, candidate)
    return int(candidate)


def as_optional_record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray)):
        return dict(value)
    return None