"""Alias normalization for model config command inputs."""

from __future__ import annotations

import re

_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


def normalize_alias(alias: str) -> str:
    """Validate and normalize a user-facing model alias."""
    trimmed = alias.strip()
    if not trimmed:
        raise ValueError("Alias cannot be empty.")
    if not _ALIAS_PATTERN.match(trimmed):
        raise ValueError("Alias must use letters, numbers, dots, underscores, colons, or dashes.")
    return trimmed
