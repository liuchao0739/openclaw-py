"""Record coercion utilities.

Mirrors packages/normalization-core/src/record-coerce.ts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def is_record(value: Any) -> bool:
    """Type guard for non-array object records at browser-safe boundaries."""
    return isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray))


def as_record(value: Any) -> dict[str, Any]:
    """Coerce object-like values to records, falling back to an empty record."""
    if isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray)):
        return dict(value)
    if value is not None and isinstance(value, object) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return {}
    return {}


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


def as_optional_object_record(value: Any) -> dict[str, Any] | None:
    """Return any object-backed record, including arrays, or None."""
    if value is None or isinstance(value, (bool, int, float, str, bytes, bytearray)):
        return None
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, object):
        return {}
    return None


def as_nullable_object_record(value: Any) -> dict[str, Any] | None:
    """Return any object-backed record, including arrays, or None."""
    return as_optional_object_record(value)


__all__ = [
    "as_nullable_object_record",
    "as_nullable_record",
    "as_optional_object_record",
    "as_optional_record",
    "as_record",
    "is_record",
    "read_string_field",
]
