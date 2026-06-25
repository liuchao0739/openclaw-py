"""Shared sender identity helpers for authorization checks."""

from __future__ import annotations

import re
from typing import Any

_CONVERSATION_LIKE_PATTERN = re.compile(
    r"(^|:)(channel|group|thread|topic|room|space|spaces):", re.IGNORECASE
)


def _is_conversation_like_identity(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized.startswith("chat_id:"):
        return True
    return bool(_CONVERSATION_LIKE_PATTERN.search(normalized))


def should_use_from_as_sender_fallback(params: dict[str, Any]) -> bool:
    """Determine if the 'from' field should be used as sender fallback.

    Returns False for conversation-like identities (chat_id:, channel:, group:, etc.)
    and for non-direct chat types.
    """
    from_value = params.get("from")
    if not from_value or not isinstance(from_value, str) or not from_value.strip():
        return False
    chat_type = (params.get("chatType") or "").strip().lower()
    if chat_type and chat_type != "direct":
        return False
    return not _is_conversation_like_identity(from_value)
