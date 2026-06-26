"""Skill filter helpers apply config, agent, and source filters to discovered skills.

Mirrors src/skills/discovery/filter.ts.
"""

from __future__ import annotations

from typing import Any, Iterable


def _normalize_string_entries(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for item in values:
        if isinstance(item, str):
            trimmed = item.strip()
            if trimmed:
                result.append(trimmed)
    return result


def _sort_unique_strings(values: list[str]) -> list[str]:
    return sorted(set(values))


def normalize_skill_filter(skill_filter: Iterable[Any] | None) -> list[str] | None:
    """Normalize an optional skill filter, preserving None as 'not configured'."""
    if skill_filter is None:
        return None
    return _normalize_string_entries(skill_filter)


def normalize_skill_filter_for_comparison(
    skill_filter: Iterable[Any] | None,
) -> list[str] | None:
    """Normalize and sort-unique a skill filter for comparison."""
    normalized = normalize_skill_filter(skill_filter)
    if normalized is None:
        return None
    return _sort_unique_strings(normalized)


def matches_skill_filter(
    cached: Iterable[Any] | None,
    next_filter: Iterable[Any] | None,
) -> bool:
    """Check if two skill filters match after normalization."""
    cached_norm = normalize_skill_filter_for_comparison(cached)
    next_norm = normalize_skill_filter_for_comparison(next_filter)
    if cached_norm is None or next_norm is None:
        return cached_norm == next_norm
    if len(cached_norm) != len(next_norm):
        return False
    return all(a == b for a, b in zip(cached_norm, next_norm))
