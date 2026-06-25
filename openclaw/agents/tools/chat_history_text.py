"""Chat history text formatting helpers.

Converts chat history entries into readable text for tool consumption.
"""

from __future__ import annotations

from typing import Any


def format_chat_history_entry(entry: dict[str, Any]) -> str:
    """Format a single chat history entry as text."""
    role = entry.get("role", "unknown")
    content = entry.get("content", "")

    if isinstance(content, str):
        return f"[{role}] {content}"

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        parts.append(text)
                elif block.get("type") == "image":
                    parts.append("[image]")
        return f"[{role}] {' '.join(parts)}" if parts else f"[{role}]"

    return f"[{role}]"


def format_chat_history(entries: list[dict[str, Any]], max_entries: int = 100) -> str:
    """Format chat history entries as a text transcript."""
    truncated = entries[-max_entries:] if len(entries) > max_entries else entries
    lines = [format_chat_history_entry(e) for e in truncated]
    if len(entries) > max_entries:
        lines.insert(0, f"[{len(entries) - max_entries} earlier entries omitted]")
    return "\n".join(lines)


def extract_text_from_content(content: Any) -> str:
    """Extract plain text from message content (string or content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts)
    return ""
