"""Provider id normalization helpers.

Mirrors packages/model-catalog-core/src/provider-id.ts.
"""

from __future__ import annotations

from typing import TypeVar

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty

_T = TypeVar("_T")


def normalize_provider_id(provider: str) -> str:
    return normalize_lowercase_string_or_empty(provider)


def normalize_provider_id_for_auth(provider: str) -> str:
    return normalize_provider_id(provider)


def find_normalized_provider_value(
    entries: dict[str, _T] | None,
    provider: str,
) -> _T | None:
    if not entries:
        return None
    provider_key = normalize_provider_id(provider)
    for key, value in entries.items():
        if normalize_provider_id(key) == provider_key:
            return value
    return None


def find_normalized_provider_key(
    entries: dict[str, object] | None,
    provider: str,
) -> str | None:
    if not entries:
        return None
    provider_key = normalize_provider_id(provider)
    for key in entries:
        if normalize_provider_id(key) == provider_key:
            return key
    return None


__all__ = [
    "find_normalized_provider_key",
    "find_normalized_provider_value",
    "normalize_lowercase_string_or_empty",
    "normalize_provider_id",
    "normalize_provider_id_for_auth",
]
