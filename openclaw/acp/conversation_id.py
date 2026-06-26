"""Normalizes ACP conversation identifiers from loose metadata values.

Mirrors src/acp/conversation-id.ts.
"""

from __future__ import annotations

from typing import Any


def normalize_conversation_text(value: Any) -> str:
    """Normalize a conversation id from a loose metadata value."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, int):
        return str(value).strip()
    return ""
