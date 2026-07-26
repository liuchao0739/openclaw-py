"""Normalization core package — string coercion utilities.

Mirrors packages/normalization-core/src/string-coerce.ts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from openclaw.packages.normalization_core.record_coerce import (
    as_nullable_record,
    as_optional_record,
    as_record,
    is_record,
    read_string_field,
)

__all__ = [
    "as_nullable_record",
    "as_optional_record",
    "as_record",
    "has_non_empty_string",
    "is_record",
    "normalize_fast_mode",
    "normalize_lowercase_string_or_empty",
    "normalize_nullable_string",
    "normalize_optional_lowercase_string",
    "normalize_optional_string",
    "normalize_optional_stringified_id",
    "normalize_optional_thread_value",
    "normalize_stringified_entries",
    "normalize_stringified_optional_string",
    "read_string_field",
    "read_string_value",
    "resolve_primary_string_value",
]


def read_string_value(value: Any) -> str | None:
    """Read a value only when it is already a string, preserving whitespace."""
    return value if isinstance(value, str) else None


def normalize_nullable_string(value: Any) -> str | None:
    """Trim string input and return None for non-strings or empty strings."""
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def normalize_optional_string(value: Any) -> str | None:
    """Trim string input and return None for non-strings or empty strings."""
    return normalize_nullable_string(value)


def normalize_stringified_optional_string(value: Any) -> str | None:
    """Stringify primitive ids/flags before applying optional string normalization."""
    if isinstance(value, str):
        return normalize_optional_string(value)
    if isinstance(value, bool):
        return normalize_optional_string(str(value).lower())
    if isinstance(value, int):
        return normalize_optional_string(str(value))
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return normalize_optional_string(str(value))
    return None


def normalize_stringified_entries(values: list[Any] | None) -> list[str]:
    """Normalize an optional array of primitive-ish values into non-empty strings."""
    return [s for s in (normalize_stringified_optional_string(v) for v in (values or [])) if s]


def normalize_optional_lowercase_string(value: Any) -> str | None:
    """Lowercase a normalized optional string."""
    result = normalize_optional_string(value)
    return result.lower() if result else None


def normalize_lowercase_string_or_empty(value: Any) -> str:
    """Lowercase a normalized string or return empty string when absent."""
    return normalize_optional_lowercase_string(value) or ""


def normalize_fast_mode(raw: Any) -> bool | str | None:
    """Parse loose boolean/fast-mode flags from strings or booleans."""
    if isinstance(raw, bool):
        return raw
    if not raw:
        return None
    key = normalize_lowercase_string_or_empty(raw)
    if key in ("off", "false", "no", "0", "disable", "disabled", "normal"):
        return False
    if key in ("on", "true", "yes", "1", "enable", "enabled", "fast"):
        return True
    if key in ("auto", "automatic"):
        return "auto"
    return None


def resolve_primary_string_value(value: Any) -> str | None:
    """Read a string directly or from an object's primary field."""
    if isinstance(value, str):
        return normalize_optional_string(value)
    if isinstance(value, Mapping):
        return normalize_optional_string(value.get("primary"))
    return None


def normalize_optional_thread_value(value: Any) -> str | int | None:
    """Normalize thread ids that may be numeric or string-backed."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value)
    return normalize_optional_string(value)


def normalize_optional_stringified_id(value: Any) -> str | None:
    """Normalize a thread/id value and stringify finite numeric ids."""
    normalized = normalize_optional_thread_value(value)
    if normalized is None:
        return None
    return str(normalized)


def has_non_empty_string(value: Any) -> bool:
    """Type guard for strings that remain non-empty after trimming."""
    return normalize_optional_string(value) is not None
