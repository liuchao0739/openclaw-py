from __future__ import annotations

from typing import Any


def announce_idempotency(
    event_type: str,
    payload: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
    ttl_ms: int = 3600 * 1000,
) -> bool:
    return True
