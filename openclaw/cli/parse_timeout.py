"""Shared CLI timeout parsers for millisecond flags and config-backed fallbacks."""

from __future__ import annotations

from typing import Any, Literal


def _parse_strict_positive_integer(value: str) -> int | None:
    """Parse a strict positive integer string."""
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return None
    if parsed > 0:
        return parsed
    return None


def parse_timeout_ms(raw: Any) -> int | None:
    """Parse a positive millisecond timeout, returning None for absent or invalid input."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, str):
        trimmed = raw.strip()
        if not trimmed:
            return None
        return _parse_strict_positive_integer(trimmed)
    return None


def _invalid_timeout(value: str | None = None) -> Exception:
    suffix = f' Received: "{value}".' if value else ""
    return ValueError(
        f"Invalid --timeout. Use a positive millisecond value, e.g. --timeout 30000.{suffix}"
    )


def parse_timeout_ms_with_fallback(
    raw: Any,
    fallback_ms: int,
    *,
    invalid_type: Literal["fallback", "error"] = "fallback",
) -> int:
    """Parse a positive timeout or return the supplied fallback for missing values."""
    if raw is None:
        return fallback_ms

    if isinstance(raw, str):
        value = raw.strip()
    elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = str(int(raw))
    else:
        if invalid_type == "error":
            raise _invalid_timeout()
        return fallback_ms

    if not value:
        if invalid_type == "error":
            raise _invalid_timeout()
        return fallback_ms

    parsed = _parse_strict_positive_integer(value)
    if parsed is None:
        raise _invalid_timeout(value)
    return parsed
