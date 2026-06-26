"""Close reason helpers keep WebSocket handshake failure text within RFC byte limits.

Mirrors src/gateway/server/close-reason.ts.
"""

from __future__ import annotations

CLOSE_REASON_MAX_BYTES = 120


def truncate_close_reason(reason: str, max_bytes: int = CLOSE_REASON_MAX_BYTES) -> str:
    """Truncate close reasons to the RFC-safe byte limit used during handshake failures."""
    if not reason:
        return "invalid handshake"
    encoded = reason.encode("utf-8")
    if len(encoded) <= max_bytes:
        return reason
    return encoded[:max_bytes].decode("utf-8", errors="ignore")
