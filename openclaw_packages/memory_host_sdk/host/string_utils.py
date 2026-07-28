from __future__ import annotations

from typing import Iterable, List, Optional


def normalize_nullable_string(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def normalize_optional_string(value: object) -> Optional[str]:
    return normalize_nullable_string(value)


def normalize_optional_lowercase_string(value: object) -> Optional[str]:
    result = normalize_optional_string(value)
    return result.lower() if result else None


def normalize_lowercase_string_or_empty(value: object) -> str:
    result = normalize_optional_lowercase_string(value)
    return result or ""


def normalize_string_entries(values: Iterable[object]) -> List[str]:
    return [s for s in (normalize_optional_string(str(v)) or "" for v in values) if s]


def unique_strings(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(values))
