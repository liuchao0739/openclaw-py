"""Parsing for the /send override command embedded in inbound auto-reply text."""

from __future__ import annotations

import re
from typing import Any, Literal

SendPolicyOverride = Literal["allow", "deny"]


def _normalize_send_policy_override(raw: str | None) -> SendPolicyOverride | None:
    if not raw or not isinstance(raw, str):
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value in ("allow", "on"):
        return "allow"
    if value in ("deny", "off"):
        return "deny"
    return None


def _strip_inbound_metadata(text: str) -> str:
    """Strip inbound metadata markers from text."""
    return re.sub(r"\x00[^:]*:[^\x00]*\x00", "", text).strip()


def _normalize_command_body(text: str) -> str:
    """Normalize a command body for matching."""
    return text.strip()


def parse_send_policy_command(raw: str | None) -> dict[str, Any]:
    """Parse /send commands and map user-facing aliases to allow, deny, or inherit."""
    if not raw:
        return {"hasCommand": False}
    trimmed = raw.strip()
    if not trimmed:
        return {"hasCommand": False}
    stripped = _strip_inbound_metadata(trimmed)
    normalized = _normalize_command_body(stripped)
    match = re.match(r"^/send(?:\s+([a-zA-Z]+))?\s*$", normalized, re.IGNORECASE)
    if not match:
        return {"hasCommand": False}
    token = match.group(1)
    if not token:
        return {"hasCommand": True}
    token_lower = token.lower()
    if token_lower in ("inherit", "default", "reset"):
        return {"hasCommand": True, "mode": "inherit"}
    mode = _normalize_send_policy_override(token_lower)
    return {"hasCommand": True, "mode": mode}
