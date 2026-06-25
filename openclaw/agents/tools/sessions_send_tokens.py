"""Session send token estimation helpers.

Estimates token counts for session send operations to prevent oversized messages.
"""

from __future__ import annotations

from typing import Any

# Rough estimate: ~4 characters per token for mixed text
_CHARS_PER_TOKEN = 4
MAX_SESSION_SEND_TOKENS = 8192


def estimate_tokens(text: str) -> int:
    """Estimate the token count for a text string."""
    if not text:
        return 0
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """Estimate the token count for a message dict."""
    content = message.get("content")
    if isinstance(content, str):
        return estimate_tokens(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if isinstance(text, str):
                    total += estimate_tokens(text)
        return total
    return 0


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """Estimate total token count for a list of messages."""
    return sum(estimate_message_tokens(m) for m in messages)


def is_within_send_limit(messages: list[dict[str, Any]], max_tokens: int = MAX_SESSION_SEND_TOKENS) -> bool:
    """Check if messages are within the send token limit."""
    return estimate_messages_tokens(messages) <= max_tokens


def truncate_messages_to_limit(
    messages: list[dict[str, Any]],
    max_tokens: int = MAX_SESSION_SEND_TOKENS,
) -> list[dict[str, Any]]:
    """Truncate messages from the head to fit within the token limit."""
    result: list[dict[str, Any]] = []
    total = 0
    for msg in reversed(messages):
        msg_tokens = estimate_message_tokens(msg)
        if total + msg_tokens > max_tokens:
            break
        result.insert(0, msg)
        total += msg_tokens
    return result
