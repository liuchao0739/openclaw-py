from __future__ import annotations

from typing import Any


def build_tool_policy(
    config: dict[str, Any] | None = None,
    permissions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "config": config or {},
        "permissions": permissions or {},
        "deniedTools": set(),
        "allowedTools": None,
    }


def is_tool_allowed(
    policy: dict[str, Any],
    tool_name: str,
) -> bool:
    denied = policy.get("deniedTools", set())
    if tool_name in denied:
        return False
    allowed = policy.get("allowedTools")
    if allowed is not None and tool_name not in allowed:
        return False
    return True
