from __future__ import annotations

from typing import Any


def build_tool_definition(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": parameters or {"type": "object", "properties": {}},
        "metadata": metadata,
    }


def validate_tool_definition(tool: dict[str, Any]) -> tuple[bool, str | None]:
    if not tool.get("name"):
        return False, "Tool definition missing 'name'"
    if not tool.get("description"):
        return False, "Tool definition missing 'description'"
    return True, None
