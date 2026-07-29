from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)

TOOL_CALL_TYPES = {"tool_use", "toolcall", "tool_call"}
TOOL_RESULT_TYPES = {"tool_result", "tool_result_error"}


def _normalize_type(value: Any) -> str:
    if isinstance(value, str):
        return normalize_optional_lowercase_string(value) or ""
    return ""


def extract_tool_call_names(message: dict) -> list[str]:
    names: set[str] = set()
    tool_name_raw = message.get("toolName") or message.get("tool_name")
    tool_name = normalize_optional_string(tool_name_raw) if isinstance(tool_name_raw, str) else None
    if tool_name:
        names.add(tool_name)

    content = message.get("content")
    if not isinstance(content, list):
        return list(names)

    for entry in content:
        if not entry or not isinstance(entry, dict):
            continue
        block_type = _normalize_type(entry.get("type"))
        if block_type not in TOOL_CALL_TYPES:
            continue
        name_raw = entry.get("name")
        name = normalize_optional_string(name_raw) if isinstance(name_raw, str) else None
        if name:
            names.add(name)

    return list(names)


def has_tool_call(message: dict) -> bool:
    return len(extract_tool_call_names(message)) > 0


def count_tool_results(message: dict) -> dict:
    content = message.get("content")
    if not isinstance(content, list):
        return {"total": 0, "errors": 0}

    total = 0
    errors = 0
    for entry in content:
        if not entry or not isinstance(entry, dict):
            continue
        block_type = _normalize_type(entry.get("type"))
        if block_type not in TOOL_RESULT_TYPES:
            continue
        total += 1
        if entry.get("is_error") is True:
            errors += 1

    return {"total": total, "errors": errors}
