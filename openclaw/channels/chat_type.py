"""Channel conversation kind normalization."""

from __future__ import annotations

from typing import Literal

ChatType = Literal["direct", "group", "channel"]


def normalize_chat_type(raw: str | None) -> ChatType | None:
    """Normalize channel-specific chat type labels into OpenClaw conversation kinds."""
    if not raw:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value in ("direct", "dm"):
        return "direct"
    if value == "group":
        return "group"
    if value == "channel":
        return "channel"
    return None
