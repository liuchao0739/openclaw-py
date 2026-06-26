"""Read the optional optimistic-write base hash from a gateway method payload.

Mirrors src/gateway/server-methods/base-hash.ts.
"""

from __future__ import annotations

from typing import Any


def resolve_base_hash_param(params: Any) -> str | None:
    """Read the optional optimistic-write base hash from a gateway method payload.

    Base hashes are optimistic-write guards. Treat missing, blank, and non-string
    values as absent so callers must opt in deliberately.
    """
    if not isinstance(params, dict):
        return None
    raw = params.get("baseHash")
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    return trimmed or None
