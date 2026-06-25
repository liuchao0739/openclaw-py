"""Shared nullable record guard for doctor config walkers."""

from __future__ import annotations

from typing import Any


def as_object_record(value: Any) -> dict[str, Any] | None:
    """Return value as a dict if it's a non-null, non-array object, else None."""
    if value is None or not isinstance(value, dict):
        return None
    return value
