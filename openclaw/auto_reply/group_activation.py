"""Group activation command parser for mention/always auto-reply modes."""

from __future__ import annotations

import re
from typing import Any, Literal

GroupActivationMode = Literal["mention", "always"]


def normalize_group_activation(raw: str | None) -> GroupActivationMode | None:
    """Normalize a raw group activation mode string."""
    if not raw or not isinstance(raw, str):
        return None
    value = raw.strip().lower()
    if value == "mention":
        return "mention"
    if value == "always":
        return "always"
    return None


def parse_activation_command(raw: str | None) -> dict[str, Any]:
    """Parse /activation commands from inbound message text."""
    if not raw:
        return {"hasCommand": False}
    trimmed = raw.strip()
    if not trimmed:
        return {"hasCommand": False}

    # Normalize /command: arg → /command arg
    normalized = re.sub(
        r"^/([^\s:]+)\s*:(.*)$",
        lambda m: f"/{m.group(1)} {m.group(2).strip()}" if m.group(2).strip() else f"/{m.group(1)}",
        trimmed,
    )

    match = re.match(r"^/activation(?:\s+([a-zA-Z]+))?\s*$", normalized, re.IGNORECASE)
    if not match:
        return {"hasCommand": False}
    mode = normalize_group_activation(match.group(1))
    return {"hasCommand": True, "mode": mode}
