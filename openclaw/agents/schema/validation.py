from __future__ import annotations

from typing import Any


def validate_agent_message_schema(message: dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(message, dict):
        return False, "Message must be a dict"
    role = message.get("role")
    if not role or role not in ("user", "assistant", "system", "tool"):
        return False, f"Invalid role: {role}"
    if role == "user" and not message.get("content"):
        return False, "User message must have content"
    return True, None


def validate_agent_tool_schema(tool: dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(tool, dict):
        return False, "Tool must be a dict"
    if not tool.get("name"):
        return False, "Tool must have a name"
    return True, None
