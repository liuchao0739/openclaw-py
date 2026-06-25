"""Announce idempotency helpers.

Prevents duplicate announce deliveries for the same session/target combination.
"""

from __future__ import annotations

from typing import Any

# Process-local set of announced delivery keys
_announced_keys: set[str] = set()


def _make_key(
    session_id: str,
    target_id: str,
    *,
    channel: str | None = None,
    agent_id: str | None = None,
) -> str:
    parts = [session_id, target_id]
    if channel:
        parts.append(channel)
    if agent_id:
        parts.append(agent_id)
    return ":".join(parts)


def has_announced(
    session_id: str,
    target_id: str,
    *,
    channel: str | None = None,
    agent_id: str | None = None,
) -> bool:
    """Check if a delivery has already been announced."""
    return _make_key(session_id, target_id, channel=channel, agent_id=agent_id) in _announced_keys


def mark_announced(
    session_id: str,
    target_id: str,
    *,
    channel: str | None = None,
    agent_id: str | None = None,
) -> bool:
    """Mark a delivery as announced. Returns True if newly announced, False if duplicate."""
    key = _make_key(session_id, target_id, channel=channel, agent_id=agent_id)
    if key in _announced_keys:
        return False
    _announced_keys.add(key)
    return True


def clear_announced() -> None:
    """Clear all announced delivery keys."""
    _announced_keys.clear()
