"""Session key helpers for agent commands (partial port)."""

from __future__ import annotations

from typing import Any, TypedDict

from openclaw.routing.session_key import normalize_agent_id


class SessionKeyResolution(TypedDict):
    sessionKey: str | None
    sessionStore: dict[str, Any]
    storePath: str


def build_explicit_session_id_session_key(*, session_id: str, agent_id: str | None = None) -> str:
    return f"agent:{normalize_agent_id(agent_id)}:explicit:{session_id.strip()}"


def resolve_stored_session_key_for_session_id(
    *,
    session_store: dict[str, Any],
    store_path: str,
    session_id: str,
) -> SessionKeyResolution:
    sid = session_id.strip()
    if not sid:
        return SessionKeyResolution(sessionKey=None, sessionStore=session_store, storePath=store_path)
    matches = [(key, entry) for key, entry in session_store.items() if entry.get("sessionId") == sid]
    if not matches:
        return SessionKeyResolution(sessionKey=None, sessionStore=session_store, storePath=store_path)
    if len(matches) == 1:
        return SessionKeyResolution(
            sessionKey=matches[0][0],
            sessionStore=session_store,
            storePath=store_path,
        )
    # Deterministic: prefer highest updatedAt, then lexicographic key
    def sort_key(item: tuple[str, Any]) -> tuple[float, str]:
        entry = item[1] or {}
        updated = entry.get("updatedAt")
        ts = float(updated) if isinstance(updated, (int, float)) else 0.0
        return (-ts, item[0])

    best = sorted(matches, key=sort_key)[0][0]
    return SessionKeyResolution(sessionKey=best, sessionStore=session_store, storePath=store_path)