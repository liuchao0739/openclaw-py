"""SQLite scalar column codecs for the cron store.

Mirrors src/cron/store/scalar-codec.ts.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


def normalize_number(value: Any) -> float | int | None:
    """Normalize SQLite number/bigint columns into Python numbers.

    Accepts int, float, and bigint-like values. Returns ``None`` for
    non-numeric values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    # bigint represented as string in some SQLite drivers
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def parse_json_object(raw: str, fallback: Any) -> Any:
    """Parse a JSON object column, returning the fallback for malformed or non-object values."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback
    return parsed if isinstance(parsed, Mapping) else fallback


def parse_json_value(raw: str, fallback: Any) -> Any:
    """Parse a JSON column without shape validation, returning the fallback only on parse failure."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def boolean_to_integer(value: bool | None) -> int | None:
    """Convert optional booleans into nullable SQLite integer flags."""
    if isinstance(value, bool):
        return 1 if value else 0
    return None


def integer_to_boolean(value: Any) -> bool | None:
    """Convert SQLite integer flags into booleans, preserving missing columns as None."""
    normalized = normalize_number(value)
    if normalized is None:
        return None
    return normalized != 0


def serialize_json(value: Any) -> str | None:
    """Serialize optional structured values for JSON columns."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def parse_json_array(raw: str | None) -> list[str] | None:
    """Parse a JSON string-array column and drop non-string entries from legacy data."""
    if not raw:
        return None
    # Use parse_json_value (not parse_json_object) because the original TS relies
    # on ``typeof [] === "object"`` — arrays pass the object check in JS.
    parsed = parse_json_value(raw, None)
    if not isinstance(parsed, list):
        return None
    return [item for item in parsed if isinstance(item, str)]
