from __future__ import annotations

from typing import Any


def tool_call_id(
    tool_name: str,
    call_index: int,
    prefix: str = "call",
) -> str:
    return f"{prefix}_{tool_name}_{call_index}"


def parse_tool_call_id(call_id: str) -> dict[str, str] | None:
    parts = call_id.split("_", 2)
    if len(parts) < 3:
        return None
    return {
        "prefix": parts[0],
        "toolName": parts[1],
        "callIndex": parts[2],
    }
