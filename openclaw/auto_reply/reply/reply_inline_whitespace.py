"""Normalizes inline directive whitespace without changing user-visible text."""

from __future__ import annotations

import re

_INLINE_HORIZONTAL_WHITESPACE_RE = re.compile(r"[^\S\n]+")


def collapse_inline_horizontal_whitespace(value: str) -> str:
    """Collapse horizontal inline whitespace while preserving line breaks."""
    return _INLINE_HORIZONTAL_WHITESPACE_RE.sub(" ", value)
