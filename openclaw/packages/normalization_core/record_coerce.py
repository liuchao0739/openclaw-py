"""Record coercion utilities.

Mirrors packages/normalization-core/src/record-coerce.ts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def is_record(value: Any) -> bool:
    """Type guard for non-array object records at browser-safe boundaries."""
    return isinstance(value, Mapping)


def as_record(value: Any) -> dict[str, Any]:
    """Coerce object-like values to records, falling back to an empty record."""
    return dict(value) if isinstance(value, Mapping) else {}


def read_string_field(record: Mapping[str, Any] | None, key: str) -> str | None:
    """Read a field only when it exists as a string."""
    value = record.get(key) if record is not None else None
    return value if isinstance(value, str) else None


def as_optional_record(value: Any) -> dict[str, Any] | None:
    """Return a non-array record or None."""
    return dict(value) if is_record(value) else None


def as_nullable_record(value: Any) -> dict[str, Any] | None:
    """Return a non-array record or None."""
    return as_optional_record(value)
