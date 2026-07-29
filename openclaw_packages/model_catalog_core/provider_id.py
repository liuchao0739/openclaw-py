from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")


def normalize_lowercase_string_or_empty(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def normalize_provider_id(provider: str) -> str:
    return normalize_lowercase_string_or_empty(provider)


def normalize_provider_id_for_auth(provider: str) -> str:
    return normalize_provider_id(provider)


def find_normalized_provider_value(
    entries: Optional[Dict[str, T]],
    provider: str,
) -> Optional[T]:
    if not entries:
        return None
    provider_key = normalize_provider_id(provider)
    for key, value in entries.items():
        if normalize_provider_id(key) == provider_key:
            return value
    return None


def find_normalized_provider_key(
    entries: Optional[Dict[str, Any]],
    provider: str,
) -> Optional[str]:
    if not entries:
        return None
    provider_key = normalize_provider_id(provider)
    for key in entries.keys():
        if normalize_provider_id(key) == provider_key:
            return key
    return None
