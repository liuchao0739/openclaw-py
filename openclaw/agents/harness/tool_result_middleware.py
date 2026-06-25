"""Runs native harness tool-result middleware around tool execution results.

The full middleware loader depends on the plugins system. This port provides
the validation/coercion helpers (which are self-contained) and a middleware
runner that accepts explicit handler lists.
"""

from __future__ import annotations

import json
from typing import Any

MAX_MIDDLEWARE_CONTENT_BLOCKS = 200
MAX_MIDDLEWARE_TEXT_CHARS = 100_000
MAX_MIDDLEWARE_IMAGE_DATA_CHARS = 5_000_000
MAX_MIDDLEWARE_CONTENT_DEPTH = 20
MAX_MIDDLEWARE_DETAILS_BYTES = 100_000
MAX_MIDDLEWARE_DETAILS_DEPTH = 20
MAX_MIDDLEWARE_DETAILS_KEYS = 1_000
_NESTED_TOOL_RESULT_BLOCK_TYPES = {"toolresult", "tool_result"}


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _truncate_utf16_safe(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max(0, max_chars)]


def is_valid_middleware_content_block(value: Any) -> bool:
    if not _is_record(value) or not isinstance(value.get("type"), str):
        return False
    if value["type"] == "text":
        return isinstance(value.get("text"), str) and len(value["text"]) <= MAX_MIDDLEWARE_TEXT_CHARS
    if value["type"] == "image":
        return (
            isinstance(value.get("mimeType"), str)
            and value["mimeType"].strip()
            and isinstance(value.get("data"), str)
            and len(value["data"]) <= MAX_MIDDLEWARE_IMAGE_DATA_CHARS
        )
    return False


def is_valid_middleware_details(value: Any, state: dict[str, Any] | None = None, depth: int = 0) -> bool:
    if state is None:
        state = {"keys": 0, "bytes": 0, "seen": set()}
    if value is None:
        return True
    if depth > MAX_MIDDLEWARE_DETAILS_DEPTH:
        return False
    if isinstance(value, str):
        state["bytes"] += len(value)
        return state["bytes"] <= MAX_MIDDLEWARE_DETAILS_BYTES
    if isinstance(value, (int, float, bool)):
        state["bytes"] += len(str(value))
        return state["bytes"] <= MAX_MIDDLEWARE_DETAILS_BYTES
    if not isinstance(value, (dict, list)):
        return False
    obj_id = id(value)
    if obj_id in state["seen"]:
        return False
    state["seen"].add(obj_id)
    if isinstance(value, list):
        state["keys"] += len(value)
        if state["keys"] > MAX_MIDDLEWARE_DETAILS_KEYS:
            return False
        for entry in value:
            if not is_valid_middleware_details(entry, state, depth + 1):
                return False
        return True
    for key, entry in value.items():
        state["keys"] += 1
        state["bytes"] += len(key)
        if state["keys"] > MAX_MIDDLEWARE_DETAILS_KEYS or state["bytes"] > MAX_MIDDLEWARE_DETAILS_BYTES:
            return False
        if not is_valid_middleware_details(entry, state, depth + 1):
            return False
    return True


def is_valid_middleware_tool_result(value: Any) -> bool:
    if not _is_record(value) or not isinstance(value.get("content"), list):
        return False
    if len(value["content"]) > MAX_MIDDLEWARE_CONTENT_BLOCKS:
        return False
    return all(is_valid_middleware_content_block(b) for b in value["content"]) and is_valid_middleware_details(
        value.get("details")
    )


def build_middleware_failure_result() -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": "Tool output unavailable due to post-processing error."}],
        "details": {"status": "error", "middlewareError": True},
    }


def sanitize_middleware_details_value(value: Any) -> Any:
    try:
        serialized = json.dumps(value, default=str)
        if len(serialized) > MAX_MIDDLEWARE_DETAILS_BYTES:
            return {"truncated": True, "originalSizeBytes": len(serialized)}
        return json.loads(serialized)
    except Exception:
        return None


def create_agent_tool_result_middleware_runner(
    ctx: dict[str, Any],
    handlers: list[Any] | None = None,
) -> Any:
    """Create a runner that applies tool-result middleware handlers."""

    class _MiddlewareRunner:
        def __init__(self) -> None:
            self._handlers = handlers

        async def apply_tool_result_middleware(self, event: dict[str, Any]) -> dict[str, Any]:
            if self._handlers is None or len(self._handlers) == 0:
                return event["result"]
            current = event["result"]
            for handler in self._handlers:
                try:
                    next_result = await handler({**event, "result": current}, ctx)
                    candidate = next_result.get("result", current) if next_result else current
                    if is_valid_middleware_tool_result(candidate):
                        current = candidate
                    else:
                        return build_middleware_failure_result()
                except Exception:
                    return build_middleware_failure_result()
            return current

    return _MiddlewareRunner()
