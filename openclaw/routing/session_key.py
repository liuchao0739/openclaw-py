"""Session key helpers (minimal port)."""

from __future__ import annotations

DEFAULT_AGENT_ID = "main"


def normalize_agent_id(agent_id: str | None) -> str:
    trimmed = (agent_id or "").strip()
    return trimmed if trimmed else DEFAULT_AGENT_ID