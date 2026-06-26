"""Small normalization helpers shared by gateway request handlers.

Mirrors src/gateway/server-methods/record-shared.ts.
"""

from __future__ import annotations

from typing import Any


def normalize_trimmed_string(value: Any) -> str | None:
    """Return a non-empty trimmed string, or None for non-string input."""
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if len(trimmed) > 0 else None
