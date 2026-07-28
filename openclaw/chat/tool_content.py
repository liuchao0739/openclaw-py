from __future__ import annotations

from typing import Any

TOOL_USE_ID_FIELDS = ("id", "tool_call_id", "toolCallId", "tool_use_id", "toolUseId")


def _normalize_tool_content_type(value: Any) -> str:
    return value.lower() if isinstance(value, str) else ""


def is_tool_call_content_type(value: Any) -> bool:
    t = _normalize_tool_content_type(value)
    return t in ("toolcall", "tool_call", "tooluse", "tool_use")


def is_tool_result_content_type(value: Any) -> bool:
    t = _normalize_tool_content_type(value)
    return t in ("toolresult", "tool_result")


def is_tool_call_block(block: dict[str, Any]) -> bool:
    return is_tool_call_content_type(block.get("type"))


def is_tool_result_block(block: dict[str, Any]) -> bool:
    return is_tool_result_content_type(block.get("type"))


def resolve_tool_block_args(block: dict[str, Any]) -> Any:
    return block.get("args") or block.get("arguments") or block.get("input")


def resolve_tool_use_id(block: dict[str, Any]) -> str | None:
    for field in TOOL_USE_ID_FIELDS:
        val = block.get(field)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return None
