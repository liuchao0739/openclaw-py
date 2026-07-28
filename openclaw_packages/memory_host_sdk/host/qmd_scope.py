from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .string_utils import normalize_lowercase_string_or_empty


def _normalize_optional_lowercase_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value.strip().lower() or None
    return None


def _parse_qmd_session_scope(key: Optional[str]) -> Dict[str, Any]:
    normalized = _normalize_qmd_session_key(key)
    if not normalized:
        return {}

    parts = [p for p in normalized.split(":") if p]
    chat_type = None

    if len(parts) >= 2 and parts[1] in ("group", "channel", "direct", "dm"):
        if "group" in parts:
            chat_type = "group"
        elif "channel" in parts:
            chat_type = "channel"
        return {
            "normalizedKey": normalized,
            "channel": _normalize_optional_lowercase_string(parts[0]),
            "chatType": chat_type or "direct",
        }

    if ":group:" in normalized:
        return {"normalizedKey": normalized, "chatType": "group"}
    if ":channel:" in normalized:
        return {"normalizedKey": normalized, "chatType": "channel"}
    return {"normalizedKey": normalized, "chatType": "direct"}


def _normalize_qmd_session_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    trimmed = key.strip()
    if not trimmed:
        return None
    parsed = _parse_agent_session_key(trimmed)
    normalized = normalize_lowercase_string_or_empty(parsed.get("rest") if parsed else trimmed)
    if normalized.startswith("subagent:"):
        return None
    return normalized


def _parse_agent_session_key(session_key: Optional[str]) -> Optional[Dict[str, str]]:
    raw = _normalize_optional_lowercase_string(session_key)
    if not raw:
        return None
    parts = [p for p in raw.split(":") if p]
    if len(parts) < 3 or parts[0] != "agent":
        return None
    rest = ":".join(parts[2:])
    return {"rest": rest} if rest else None


def is_qmd_scope_allowed(scope: Dict[str, Any], session_key: Optional[str] = None) -> bool:
    if not scope:
        return True

    parsed = _parse_qmd_session_scope(session_key)
    channel = parsed.get("channel")
    chat_type = parsed.get("chatType")
    normalized_key = parsed.get("normalizedKey", "")
    raw_key = normalize_lowercase_string_or_empty(session_key or "")

    for rule in scope.get("rules", []):
        if not rule:
            continue
        match = rule.get("match", {})

        if match.get("channel") and match["channel"] != channel:
            continue
        if match.get("chatType") and match["chatType"] != chat_type:
            continue

        normalized_prefix = _normalize_optional_lowercase_string(match.get("keyPrefix"))
        raw_prefix = _normalize_optional_lowercase_string(match.get("rawKeyPrefix"))

        if raw_prefix and not raw_key.startswith(raw_prefix):
            continue
        if normalized_prefix:
            is_legacy_raw = normalized_prefix.startswith("agent:")
            if is_legacy_raw:
                if not raw_key.startswith(normalized_prefix):
                    continue
            elif not normalized_key.startswith(normalized_prefix):
                continue

        return rule.get("action") == "allow"

    fallback = scope.get("default", "allow")
    return fallback == "allow"


def derive_qmd_scope_channel(key: Optional[str]) -> Optional[str]:
    return _parse_qmd_session_scope(key).get("channel")


def derive_qmd_scope_chat_type(key: Optional[str]) -> Optional[str]:
    return _parse_qmd_session_scope(key).get("chatType")
