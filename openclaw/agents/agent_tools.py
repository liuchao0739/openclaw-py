from __future__ import annotations

from typing import Any


def resolve_agent_tools(
    config: dict[str, Any] | None = None,
    permissions: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    config = config or {}
    permissions = permissions or {}

    tools: list[dict[str, Any]] = [
        {
            "name": "bash",
            "description": "Execute bash commands in the terminal",
            "enabled": True,
        },
        {
            "name": "read_file",
            "description": "Read file contents",
            "enabled": True,
        },
        {
            "name": "write_file",
            "description": "Write or update file contents",
            "enabled": True,
        },
        {
            "name": "web_search",
            "description": "Search the web for information",
            "enabled": config.get("webSearchEnabled", True),
        },
    ]

    denied = permissions.get("deniedTools", set())
    result = []
    for tool in tools:
        if tool["name"] in denied:
            continue
        if not tool.get("enabled", True):
            continue
        result.append(tool)
    return result


def register_agent_tool(
    name: str,
    handler: Any = None,
    description: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "handler": handler,
        "description": description,
        "enabled": True,
        **kwargs,
    }
