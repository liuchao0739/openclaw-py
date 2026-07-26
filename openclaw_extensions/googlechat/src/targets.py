"""Google Chat target normalization helpers.

Mirrors extensions/googlechat/src/targets.ts.
"""

from __future__ import annotations

import re

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

_PREFIX_RE = re.compile(r"^(googlechat|google-chat|gchat):", re.IGNORECASE)
_USER_PREFIX_RE = re.compile(r"^user:(users/)?", re.IGNORECASE)
_SPACE_PREFIX_RE = re.compile(r"^space:(spaces/)?", re.IGNORECASE)


def is_google_chat_user_target(value: str) -> bool:
    return normalize_lowercase_string_or_empty(value).startswith("users/")


def is_google_chat_space_target(value: str) -> bool:
    return normalize_lowercase_string_or_empty(value).startswith("spaces/")


def normalize_google_chat_target(raw: str | None = None) -> str | None:
    trimmed = (raw or "").strip()
    if not trimmed:
        return None
    without_prefix = _PREFIX_RE.sub("", trimmed)
    normalized = _USER_PREFIX_RE.sub("users/", without_prefix)
    normalized = _SPACE_PREFIX_RE.sub("spaces/", normalized)
    if is_google_chat_user_target(normalized):
        suffix = normalized[len("users/") :]
        if "@" in suffix:
            return f"users/{normalize_lowercase_string_or_empty(suffix)}"
        return normalized
    if is_google_chat_space_target(normalized):
        return normalized
    if "@" in normalized:
        return f"users/{normalize_lowercase_string_or_empty(normalized)}"
    return normalized
