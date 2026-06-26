"""Session kind helpers classify cron, interactive, and channel-backed sessions.

Mirrors src/sessions/classify-session-kind.ts.
"""

from __future__ import annotations

from typing import Any, Literal

SessionKind = Literal["cron", "direct", "group", "global", "spawn-child", "unknown"]


def _is_cron_session_key(key: str) -> bool:
    """Check if a session key has the cron key shape."""
    return key.startswith("cron:") or ":cron:" in key


def classify_session_kind(
    key: str,
    entry: dict[str, Any] | None = None,
) -> str:
    """Classify a session key + entry into a display kind.

    Evaluation order matters — more-specific signals take priority:
    1. sentinel keys ("global", "unknown")
    2. cron key shape
    3. spawn-child (entry has spawnedBy)
    4. group/channel chatType or key-shape substring
    5. fallback: "direct"
    """
    if key == "global":
        return "global"
    if key == "unknown":
        return "unknown"
    if _is_cron_session_key(key):
        return "cron"
    if entry and entry.get("spawnedBy"):
        return "spawn-child"
    if entry and entry.get("chatType") in ("group", "channel"):
        return "group"
    if ":group:" in key or ":channel:" in key:
        return "group"
    return "direct"
