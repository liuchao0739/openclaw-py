"""Gateway server-methods package — base hash and shared normalization helpers."""

from .base_hash import resolve_base_hash_param
from .record_shared import normalize_trimmed_string

__all__ = [
    "resolve_base_hash_param",
    "normalize_trimmed_string",
]
