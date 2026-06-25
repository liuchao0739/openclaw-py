"""Normalizes tool result content for chat transcript rendering."""

from __future__ import annotations

from typing import Any

TOOL_USE_ID_FIELDS = ("id", "tool_call_id", "toolCallId", "tool_use_id", "toolUseId")


def _normalize_tool_content_type(value: Any) -> str:
    return value.lower() if isinstance(value, str) else ""


def is_tool_call_content_type(value: Any) -> bool:
    """Accept tool-call content type spellings from provider SDKs and transcripts."""
    t = _normalize_tool_content_type(value)
    return t in ("toolcall", "tool_call", "tooluse", "tool_use")


def is_tool_result_content_type(value: Any) -> bool:
    """Accept tool-result content type spellings from provider SDKs and transcripts."""
    t = _normalize_tool_content_type(value)
    return t in ("toolresult", "tool_result")


def is_tool_call_block(block: dict[str, Any]) -> bool:
    """Narrow unknown chat content blocks to provider-shaped tool-call blocks."""
    return is_tool_call_content_type(block.get("type"))


def is_tool_result_block(block: dict[str, Any]) -> bool:
    """Narrow unknown chat content blocks to provider-shaped tool-result blocks."""
    return is_tool_result_content_type(block.get("type"))


def resolve_tool_block_args(block: dict[str, Any]) -> Any:
    """Read the argument payload across common provider field names."""
    return block.get("args") or block.get("arguments") or block.get("input")


def resolve_tool_use_id(block: dict[str, Any]) -> str | None:
    """Read the stable tool-use id across snake_case and camelCase field names."""
    for field in TOOL_USE_ID_FIELDS:
        val = block.get(field)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return None
