from __future__ import annotations

from typing import Any


def build_hook_agent_context(
    plugin_id: str,
    session_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pluginId": plugin_id,
        "sessionId": session_id,
        "config": config or {},
        "state": {},
    }


def resolve_hook_decision(
    context: dict[str, Any],
    hooks: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "proceed": True,
        "context": context,
    }
