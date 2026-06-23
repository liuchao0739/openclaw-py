"""Google turn ordering helpers for assistant-first transcripts."""

from __future__ import annotations

from typing import Any

GOOGLE_TURN_ORDER_BOOTSTRAP_TEXT = "(session bootstrap)"


def sanitize_google_assistant_first_ordering(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not messages:
        return messages
    first = messages[0]
    role = first.get("role")
    content = first.get("content")
    if (
        role == "user"
        and isinstance(content, str)
        and content.strip() == GOOGLE_TURN_ORDER_BOOTSTRAP_TEXT
    ):
        return messages
    if role != "assistant":
        return messages
    bootstrap: dict[str, Any] = {
        "role": "user",
        "content": GOOGLE_TURN_ORDER_BOOTSTRAP_TEXT,
    }
    return [bootstrap, *messages]