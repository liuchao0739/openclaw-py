"""Normalized account id helpers.

Mirrors src/routing/account-id.ts.
"""

from __future__ import annotations

import re

from openclaw.infra.prototype_keys import is_blocked_object_key
from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

DEFAULT_ACCOUNT_ID = "default"

_VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
_INVALID_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
_LEADING_DASH_RE = re.compile(r"^-+")
_TRAILING_DASH_RE = re.compile(r"-+$")


def _canonicalize_account_id(value: str) -> str:
    normalized = normalize_lowercase_string_or_empty(value)
    if _VALID_ID_RE.match(value):
        return normalized
    return _INVALID_CHARS_RE.sub("-", normalized).lstrip("-").rstrip("-")[:64]


def _normalize_canonical_account_id(value: str) -> str | None:
    canonical = _canonicalize_account_id(value)
    if not canonical or is_blocked_object_key(canonical):
        return None
    return canonical


def normalize_account_id(value: str | None = None) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_ACCOUNT_ID
    return _normalize_canonical_account_id(trimmed) or DEFAULT_ACCOUNT_ID


def normalize_optional_account_id(value: str | None = None) -> str | None:
    trimmed = (value or "").strip()
    if not trimmed:
        return None
    return _normalize_canonical_account_id(trimmed)
