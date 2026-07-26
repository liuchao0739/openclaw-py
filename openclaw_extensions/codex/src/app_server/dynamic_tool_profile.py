"""Codex dynamic tool profile filtering."""

from __future__ import annotations

from typing import Any

CODEX_APP_SERVER_OWNED_DYNAMIC_TOOL_EXCLUDES = [
    "message",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    "session_status",
    "agents_list",
    "cron",
    "gateway",
    "nodes",
    "image",
]


def filter_codex_dynamic_tools(tools: list[dict[str, Any]], plugin_config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    plugin_config = plugin_config or {}
    excludes = {
        *CODEX_APP_SERVER_OWNED_DYNAMIC_TOOL_EXCLUDES,
        *(str(name) for name in plugin_config.get("codexDynamicToolsExclude") or [] if str(name).strip()),
    }
    return [tool for tool in tools if str(tool.get("name") or "").strip() not in excludes]
