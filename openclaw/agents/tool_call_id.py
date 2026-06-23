"""Tool call id extraction (tool-call-id.ts subset)."""

from __future__ import annotations

from typing import Any

_TOOL_CALL_TYPES = frozenset({"toolCall", "toolUse", "functionCall"})


def _opt_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s or None


def extract_tool_calls_from_assistant(msg: dict[str, Any]) -> list[dict[str, str | None]]:
    content = msg.get("content")
    if not isinstance(content, list):
        return []
    out: list[dict[str, str | None]] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if not isinstance(btype, str) or btype not in _TOOL_CALL_TYPES:
            continue
        bid = _opt_str(block.get("id"))
        if not bid:
            continue
        name = block.get("name")
        out.append({"id": bid, "name": name if isinstance(name, str) else None})
    return out


def extract_tool_result_id(msg: dict[str, Any]) -> str | None:
    record = msg
    for key in (
        "toolCallId",
        "toolUseId",
        "tool_call_id",
        "tool_use_id",
        "callId",
        "call_id",
    ):
        v = _opt_str(record.get(key))
        if v:
            return v
    return None