"""String normalization utilities.

Mirrors packages/normalization-core/src/string-normalization.ts.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any, TypeVar

from .string_coerce import normalize_optional_lowercase_string, normalize_optional_string

_T = TypeVar("_T")


def normalize_string_entries(list_values: Iterable[Any] | None = None) -> list[str]:
    """Coerce entries to strings, trim them, and drop empty results."""
    return [
        normalized
        for entry in (list_values or [])
        if (normalized := normalize_optional_string(str(entry)))
    ]


def normalize_string_entries_lower(list_values: Iterable[Any] | None = None) -> list[str]:
    """Normalize string entries and lowercase each retained value."""
    return [
        normalize_optional_lowercase_string(entry) or ""
        for entry in normalize_string_entries(list_values)
    ]


def unique_values(values: Iterable[_T]) -> list[_T]:
    """Return first-seen unique values while preserving insertion order."""
    return list(dict.fromkeys(values))


def unique_strings(values: Iterable[str]) -> list[str]:
    """Return first-seen unique strings while preserving insertion order."""
    return unique_values(values)


def sort_unique_strings(values: Iterable[str]) -> list[str]:
    """Return unique strings sorted with stable ASCII comparison."""
    return sorted(unique_strings(values))


def normalize_unique_string_entries(values: Iterable[Any] | None = None) -> list[str]:
    """Normalize entries, remove duplicates, and preserve first-seen order."""
    return unique_strings(normalize_string_entries(list(values) if values is not None else None))


def normalize_unique_string_entries_lower(values: Iterable[Any] | None = None) -> list[str]:
    """Lowercase normalized entries, remove empties/duplicates, and preserve first-seen order."""
    return unique_strings(
        [entry for entry in normalize_string_entries_lower(values) if entry],
    )


def normalize_sorted_unique_string_entries(values: Iterable[Any] | None = None) -> list[str]:
    """Normalize entries, remove duplicates, and return sorted output."""
    return sort_unique_strings(normalize_unique_string_entries(values))


def normalize_trimmed_string_list(value: Any) -> list[str]:
    """Normalize array-backed string lists and reject non-array input as empty."""
    if not isinstance(value, list):
        return []
    return [
        normalized
        for entry in value
        if (normalized := normalize_optional_string(entry))
    ]


def normalize_unique_trimmed_string_list(value: Any) -> list[str]:
    """Normalize an array-backed string list and remove duplicates."""
    return unique_strings(normalize_trimmed_string_list(value))


def normalize_sorted_unique_trimmed_string_list(value: Any) -> list[str]:
    """Normalize an array-backed string list, remove duplicates, and sort it."""
    return sort_unique_strings(normalize_trimmed_string_list(value))


def normalize_optional_trimmed_string_list(value: Any) -> list[str] | None:
    """Return None instead of an empty normalized array-backed string list."""
    normalized = normalize_trimmed_string_list(value)
    return normalized if normalized else None


def normalize_array_backed_trimmed_string_list(value: Any) -> list[str] | None:
    """Return None for non-arrays but preserve an empty array for explicit arrays."""
    if not isinstance(value, list):
        return None
    return normalize_trimmed_string_list(value)


def normalize_single_or_trimmed_string_list(value: Any) -> list[str]:
    """Normalize either a single string-like value or an array-backed string list."""
    if isinstance(value, list):
        return normalize_trimmed_string_list(value)
    normalized = normalize_optional_string(value)
    return [normalized] if normalized else []


def normalize_unique_single_or_trimmed_string_list(value: Any) -> list[str]:
    """Normalize single-or-array string input and remove duplicates."""
    return unique_strings(normalize_single_or_trimmed_string_list(value))


def normalize_csv_or_loose_string_list(value: Any) -> list[str]:
    """Parse either array entries or comma-separated string entries into trimmed values."""
    if isinstance(value, list):
        return normalize_string_entries(value)
    if isinstance(value, str):
        return [entry for entry in (part.strip() for part in value.split(",")) if entry]
    return []


def _normalize_slug_input(raw: str | None) -> str:
    lowered = normalize_optional_lowercase_string(raw) or ""
    return unicodedata.normalize("NFC", lowered)


def _is_letter_mark_or_number(char: str) -> bool:
    return unicodedata.category(char)[0] in ("L", "M", "N")


def _is_hyphen_slug_char(char: str) -> bool:
    return char in "#@._+-" or _is_letter_mark_or_number(char)


def _is_at_hash_slug_char(char: str) -> bool:
    return char == "-" or _is_letter_mark_or_number(char)


def normalize_hyphen_slug(raw: str | None = None) -> str:
    """Normalize user-facing names into permissive lowercase slugs that may keep #/@/._+."""
    trimmed = _normalize_slug_input(raw)
    if not trimmed:
        return ""
    dashed = re.sub(r"\s+", "-", trimmed)
    cleaned = "".join(char if _is_hyphen_slug_char(char) else "-" for char in dashed)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return re.sub(r"^[-.]+|[-.]+$", "", cleaned)


def normalize_at_hash_slug(raw: str | None = None) -> str:
    """Normalize @/#-prefixed channel names into strict lowercase hyphen slugs without the prefix."""
    trimmed = _normalize_slug_input(raw)
    if not trimmed:
        return ""
    without_prefix = re.sub(r"^[@#]+", "", trimmed)
    dashed = re.sub(r"[\s_]+", "-", without_prefix)
    cleaned = "".join(char if _is_at_hash_slug_char(char) else "-" for char in dashed)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return re.sub(r"^-+|-+$", "", cleaned)


__all__ = [
    "normalize_array_backed_trimmed_string_list",
    "normalize_at_hash_slug",
    "normalize_csv_or_loose_string_list",
    "normalize_hyphen_slug",
    "normalize_optional_trimmed_string_list",
    "normalize_single_or_trimmed_string_list",
    "normalize_sorted_unique_string_entries",
    "normalize_sorted_unique_trimmed_string_list",
    "normalize_string_entries",
    "normalize_string_entries_lower",
    "normalize_trimmed_string_list",
    "normalize_unique_single_or_trimmed_string_list",
    "normalize_unique_string_entries",
    "normalize_unique_string_entries_lower",
    "normalize_unique_trimmed_string_list",
    "sort_unique_strings",
    "unique_strings",
    "unique_values",
]
