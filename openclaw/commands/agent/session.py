"""Session key helpers for CLI and gateway dispatch paths."""

from __future__ import annotations

from typing import Any


def build_explicit_session_id_session_key(
    agent_id: str,
    session_id: str,
    *,
    channel: str | None = None,
    scope: str | None = None,
) -> str:
    """Build a session key from an explicit session id."""
    parts = ["agent", agent_id]
    if channel:
        parts.append(channel)
    if scope:
        parts.append(scope)
    parts.append(session_id)
    return ":".join(parts)


def resolve_session_key_for_request(
    params: dict[str, Any],
) -> str | None:
    """Resolve a session key for a gateway request from params.

    Deferred to agents/command/session module; this stub provides basic resolution.
    """
    session_key = params.get("sessionKey")
    if session_key and isinstance(session_key, str) and session_key.strip():
        return session_key.strip()

    agent_id = params.get("agentId", "main")
    session_id = params.get("sessionId")
    if session_id and isinstance(session_id, str) and session_id.strip():
        return build_explicit_session_id_session_key(
            agent_id,
            session_id.strip(),
            channel=params.get("channel"),
            scope=params.get("scope"),
        )

    return None
