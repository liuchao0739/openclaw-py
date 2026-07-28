"""Assistant identity helpers normalize assistant identity labels and metadata."""

from __future__ import annotations


def coerce_identity_value(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) <= max_length:
        return trimmed
    return trimmed[:max_length]
