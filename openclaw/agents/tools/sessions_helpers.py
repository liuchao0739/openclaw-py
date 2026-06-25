"""Session helpers for tool implementations.

Provides session resolution, target identification, and announce helpers
used by session-related tools.
"""

from __future__ import annotations

from typing import Any


def resolve_session_target(params: dict[str, Any]) -> dict[str, Any]:
    """Resolve session target parameters from tool params."""
    return {
        "sessionId": params.get("sessionId"),
        "sessionKey": params.get("sessionKey"),
        "agentId": params.get("agentId"),
        "channelId": params.get("channelId"),
        "chatId": params.get("chatId"),
    }


def is_valid_session_key(key: str | None) -> bool:
    """Check if a session key follows the expected format."""
    if not key or not isinstance(key, str):
        return False
    return key.startswith("agent:") or key.startswith("global:") or key.startswith("channel:")


def parse_session_key(key: str) -> dict[str, str | None]:
    """Parse a session key into its components."""
    if not key:
        return {"agentId": None, "channel": None, "scope": None, "target": None}
    parts = key.split(":")
    if len(parts) >= 2 and parts[0] == "agent":
        return {
            "agentId": parts[1] if len(parts) > 1 else None,
            "channel": parts[2] if len(parts) > 2 else None,
            "scope": parts[3] if len(parts) > 3 else None,
            "target": parts[4] if len(parts) > 4 else None,
        }
    return {"agentId": None, "channel": None, "scope": None, "target": None}


def format_session_display_name(
    agent_id: str | None = None,
    channel: str | None = None,
    target: str | None = None,
) -> str:
    """Format a display name for a session target."""
    parts: list[str] = []
    if agent_id:
        parts.append(agent_id)
    if channel:
        parts.append(channel)
    if target:
        parts.append(target)
    return "/".join(parts) if parts else "default"
