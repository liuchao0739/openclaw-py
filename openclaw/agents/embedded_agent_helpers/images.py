"""Sanitize historical message images and empty content blocks (images.ts subset)."""

from __future__ import annotations

from typing import Any

EMPTY_CONTENT_PLACEHOLDER = "[empty content omitted]"


def is_empty_assistant_message_content(message: dict[str, Any]) -> bool:
    content = message.get("content")
    if content is None:
        return True
    if not isinstance(content, list):
        return False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            return False
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            return False
    return True


def _drop_empty_text_blocks(content: list[Any]) -> list[Any]:
    out: list[Any] = []
    for block in content:
        if not isinstance(block, dict):
            out.append(block)
            continue
        if block.get("type") != "text":
            out.append(block)
            continue
        text = block.get("text")
        if isinstance(text, str) and not text.strip():
            continue
        out.append(block)
    return out


def _ensure_non_empty_content(content: list[Any]) -> list[Any]:
    if content:
        return content
    return [{"type": "text", "text": EMPTY_CONTENT_PLACEHOLDER}]


async def sanitize_session_messages_images(
    messages: list[dict[str, Any]],
    label: str,
    *,
    sanitize_mode: str = "full",
) -> list[dict[str, Any]]:
    del label
    allow_non_image = sanitize_mode == "full"
    out: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            out.append(msg)
            continue
        role = msg.get("role")
        new_msg = dict(msg)
        content = msg.get("content")
        if isinstance(content, list) and allow_non_image:
            filtered = _drop_empty_text_blocks(content)
            if role == "assistant" and not filtered and is_empty_assistant_message_content(msg):
                new_msg["content"] = _ensure_non_empty_content([])
            else:
                new_msg["content"] = _ensure_non_empty_content(filtered) if role == "assistant" else filtered
        out.append(new_msg)
    return out