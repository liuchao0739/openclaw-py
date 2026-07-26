"""Codex dynamic tool bridge helpers."""

from __future__ import annotations

from typing import Any


def create_codex_dynamic_tool_bridge(params: dict[str, Any]) -> dict[str, Any]:
    tools = params.get("tools") or []
    direct_tool_names = {
        str(name).strip()
        for name in (params.get("directToolNames") or [])
        if str(name).strip()
    }
    loading = params.get("loading") or "searchable"
    specs: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        spec: dict[str, Any] = {
            "name": name,
            "description": str(tool.get("description") or ""),
            "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
            "deferLoading": loading == "searchable" and name not in direct_tool_names,
        }
        specs.append(spec)
    return {"specs": specs}
