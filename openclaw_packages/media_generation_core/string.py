"""Shared string normalization helpers for media-generation packages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string

__all__ = ["normalize_optional_string", "unique_trimmed_strings"]


def unique_trimmed_strings(values: Sequence[Any]) -> list[str]:
    """Return unique trimmed strings while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_optional_string(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
