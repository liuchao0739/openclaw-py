"""Silent reply policy helpers for automated reply suppression."""

from __future__ import annotations

from typing import Any, Literal

SilentReplyPolicy = Literal["allow", "disallow"]
SilentReplyConversationType = Literal["direct", "group", "internal"]

DEFAULT_SILENT_REPLY_POLICY: dict[str, str] = {
    "direct": "disallow",
    "group": "allow",
    "internal": "allow",
}


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def classify_silent_reply_conversation_type(
    session_key: str | None = None,
    surface: str | None = None,
    conversation_type: str | None = None,
) -> str:
    if conversation_type is not None:
        return conversation_type
    normalized_session_key = _normalize_lowercase_or_empty(session_key)
    if ":group:" in normalized_session_key or ":channel:" in normalized_session_key:
        return "group"
    if ":direct:" in normalized_session_key or ":dm:" in normalized_session_key:
        return "direct"
    normalized_surface = _normalize_lowercase_or_empty(surface)
    if normalized_surface == "webchat":
        return "direct"
    return "internal"


def resolve_silent_reply_policy_from_policies(
    conversation_type: str,
    default_policy: dict[str, str] | None = None,
    surface_policy: dict[str, str] | None = None,
) -> str:
    if conversation_type == "direct":
        return "disallow"
    if surface_policy and conversation_type in surface_policy:
        return surface_policy[conversation_type]
    if default_policy and conversation_type in default_policy:
        return default_policy[conversation_type]
    return DEFAULT_SILENT_REPLY_POLICY.get(conversation_type, "allow")
