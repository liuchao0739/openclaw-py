"""Shared doctor allowlist predicates for normalized sender lists."""

from __future__ import annotations

from typing import Any


def _normalize_string_entries(entries: list[Any] | None) -> list[str]:
    if not entries:
        return []
    result: list[str] = []
    for entry in entries:
        s = str(entry).strip() if entry is not None else ""
        if s:
            result.append(s)
    return result


def has_allow_from_entries(lst: list[Any] | None) -> bool:
    """Return True when an allowFrom-like list has at least one normalized sender entry."""
    return isinstance(lst, list) and len(_normalize_string_entries(lst)) > 0
