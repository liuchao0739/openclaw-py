"""Session message text extraction helpers.

Extracts and normalizes text from session messages for tool consumption.
"""

from __future__ import annotations

from typing import Any


def extract_session_message_text(message: dict[str, Any]) -> str:
    """Extract text content from a session message."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype == "text":
                    text = block.get("text", "")
                    if isinstance(text, str):
                        parts.append(text)
                elif btype == "toolCall":
                    name = block.get("name", "")
                    parts.append(f"[tool: {name}]")
        return "\n".join(parts)
    return ""


def is_assistant_message(message: dict[str, Any]) -> bool:
    """Check if a message is from the assistant."""
    return message.get("role") == "assistant"


def is_user_message(message: dict[str, Any]) -> bool:
    """Check if a message is from the user."""
    return message.get("role") == "user"


def is_tool_result_message(message: dict[str, Any]) -> bool:
    """Check if a message is a tool result."""
    return message.get("role") in ("toolResult", "tool")


def get_message_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool call blocks from a message."""
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") == "toolCall"]
