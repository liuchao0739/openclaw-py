"""Node presence helpers normalize live node presence and heartbeat metadata."""

from __future__ import annotations

from typing import Any


NODE_PRESENCE_ALIVE_EVENT = "node.presence.alive"

_NODE_PRESENCE_ALIVE_REASONS = [
    "background",
    "silent_push",
    "bg_app_refresh",
    "significant_location",
    "manual",
    "connect",
]

_NODE_PRESENCE_ALIVE_REASON_SET = set(_NODE_PRESENCE_ALIVE_REASONS)


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value or None


def normalize_node_presence_alive_reason(value: Any) -> str:
    normalized = _normalize_optional_string(value)
    if normalized:
        normalized = normalized.lower()
        if normalized in _NODE_PRESENCE_ALIVE_REASON_SET:
            return normalized
    return "background"
