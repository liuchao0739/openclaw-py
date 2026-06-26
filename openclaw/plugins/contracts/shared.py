"""Shared contract utilities.

Mirrors src/plugins/contracts/shared.ts.
"""

from __future__ import annotations

from typing import Callable, Iterable


def unique_strings(
    values: Iterable[str] | None,
    normalize: Callable[[str], str] = lambda v: v,
) -> list[str]:
    """Return unique normalized string values while preserving first-seen order."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        if not isinstance(value, str):
            continue
        normalized = normalize(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
