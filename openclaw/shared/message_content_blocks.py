"""Visit object content blocks in assistant/user message payloads."""

from __future__ import annotations

from typing import Any, Callable


def visit_object_content_blocks(
    message: Any,
    visitor: Callable[[dict[str, Any]], None],
) -> None:
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        visitor(block)
