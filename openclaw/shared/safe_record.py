"""Defensive object guards for values that may have hostile traps."""

from __future__ import annotations

from typing import Any


def is_record(value: Any) -> bool:
    try:
        return bool(value) and isinstance(value, dict)
    except Exception:
        return False


def read_record_value(value: Any, key: str) -> Any:
    if not is_record(value):
        return None
    try:
        return value.get(key)
    except Exception:
        return None


def copy_array_entries(value: Any) -> list[Any]:
    try:
        is_array = isinstance(value, list)
    except Exception:
        return []
    if not is_array:
        return []
    array = value
    try:
        length = len(array)
    except Exception:
        return []
    entries: list[Any] = []
    for index in range(length):
        try:
            entries.append(array[index])
        except Exception:
            continue
    return entries


def copy_record_entries(value: Any) -> list[tuple[str, Any]]:
    if not is_record(value):
        return []
    try:
        keys = list(value.keys())
    except Exception:
        return []
    entries: list[tuple[str, Any]] = []
    for key in keys:
        entry = read_record_value(value, key)
        if is_record(entry):
            entries.append((key, entry))
    return entries
