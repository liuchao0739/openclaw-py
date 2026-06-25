"""Heartbeat reply payload selector for multi-payload auto-reply results."""

from __future__ import annotations

from typing import Any


def has_outbound_reply_content(payload: dict[str, Any]) -> bool:
    """Check if a reply payload has outbound content suitable for heartbeat delivery."""
    if not payload:
        return False
    text = payload.get("text")
    if text and isinstance(text, str) and text.strip():
        return True
    content = payload.get("content")
    if isinstance(content, list) and len(content) > 0:
        return True
    return False


def resolve_heartbeat_reply_payload(
    reply_result: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Pick the last outbound-capable reply payload for heartbeat delivery."""
    if not reply_result:
        return None
    if not isinstance(reply_result, list):
        return reply_result
    for payload in reversed(reply_result):
        if payload and has_outbound_reply_content(payload):
            return payload
    return None
