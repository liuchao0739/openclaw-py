from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def format_status_display(status: Dict[str, Any]) -> str:
    status_type = status.get("type", "")
    status_value = status.get("value", "")
    if status_type == "heartbeat":
        return f"[heartbeat] {status_value}"
    if status_type == "error":
        return f"[error] {status_value}"
    if status_type == "progress":
        return f"[progress] {status_value}"
    return str(status_value)


def format_tool_params(params: Dict[str, Any]) -> str:
    return json.dumps(params, ensure_ascii=False)


def format_tool_result(result: Any) -> str:
    return json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result


def format_chunk_source(source: Dict[str, Any]) -> str:
    path = source.get("path", "")
    return f"[{path}]"


def format_memory_search_result(result: Dict[str, Any]) -> str:
    chunk = result.get("chunk", {})
    source = chunk.get("source", {})
    content = chunk.get("content", "")
    return f"{format_chunk_source(source)} {content}"
