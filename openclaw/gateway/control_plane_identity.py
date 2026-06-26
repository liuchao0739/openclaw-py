"""Normalizes an optional control-plane identity field without creating empty keys.

Mirrors src/gateway/control-plane-identity.ts.
"""

from __future__ import annotations

from typing import Any


def normalize_control_plane_identity_part(value: Any, fallback: str) -> str:
    """Normalize an optional control-plane identity field.

    Returns the trimmed string if non-empty, otherwise the fallback.
    Non-string values return the fallback.
    """
    if not isinstance(value, str):
        return fallback
    normalized = value.strip()
    return normalized if len(normalized) > 0 else fallback
