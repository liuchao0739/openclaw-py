"""Thread id helpers normalize channel topic/thread identifiers before payload
construction and route matching.

Mirrors src/infra/outbound/thread-id.ts.
"""

from __future__ import annotations

from typing import Any


def normalize_outbound_thread_id(value: Any) -> str | None:
    """Normalize channel thread/topic ids before outbound payload construction.

    Accepts string or number, returns stringified trimmed value or None.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return str(int(value))
    return None
