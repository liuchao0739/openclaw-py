"""Escape text so it can be embedded literally inside a RegExp pattern.

Mirrors src/shared/regexp.ts.
"""

from __future__ import annotations

import re


def escape_regexp(value: str) -> str:
    """Escape text for use in a regex pattern."""
    if not isinstance(value, str):
        return ""
    return re.escape(value)
