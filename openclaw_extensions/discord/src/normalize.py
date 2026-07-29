import re
from typing import Any, Dict, List, Optional, Union

from .target_parsing import parse_discord_target


def normalize_discord_messaging_target(raw: str) -> Optional[str]:
    target = parse_discord_target(raw, {"defaultKind": "channel"})
    return target["normalized"] if target else None


def normalize_discord_outbound_target(
    to: Optional[str] = None,
    allow_from: Optional[List[str]] = None,
) -> Dict[str, Any]:
    trimmed = (to or "").strip()
    if not trimmed:
        return {
            "ok": False,
            "error": Exception(
                'Discord recipient is required. Use "channel:<id>" for channels or "user:<id>" for DMs.'
            ),
        }
    if re.match(r"^\d+$", trimmed):
        if allow_from_contains_discord_user_id(allow_from, trimmed):
            return {"ok": True, "to": f"user:{trimmed}"}
        return {"ok": True, "to": f"channel:{trimmed}"}
    return {"ok": True, "to": trimmed}


def allow_from_contains_discord_user_id(
    allow_from: Optional[List[str]],
    user_id: str,
) -> bool:
    normalized_user_id = user_id.strip()
    if not normalized_user_id:
        return False
    for entry in (allow_from or []):
        if normalize_allow_from_discord_user_id(entry) == normalized_user_id:
            return True
    return False


def normalize_allow_from_discord_user_id(entry: str) -> Optional[str]:
    trimmed = entry.strip().lower()
    if not trimmed or trimmed == "*":
        return None
    mention_match = re.match(r"^<@!?(\d+)>$", trimmed)
    if mention_match:
        return mention_match.group(1)
    prefixed_match = re.match(r"^(?:discord:)?user:(\d+)$", trimmed)
    if prefixed_match:
        return prefixed_match.group(1)
    discord_match = re.match(r"^discord:(\d+)$", trimmed)
    if discord_match:
        return discord_match.group(1)
    return trimmed if re.match(r"^\d+$", trimmed) else None


def looks_like_discord_target_id(raw: str) -> bool:
    trimmed = raw.strip()
    if not trimmed:
        return False
    if re.match(r"^<@!?\d+>$", trimmed):
        return True
    if re.match(r"^(user|channel|discord):", trimmed, re.I):
        return True
    if re.match(r"^\d{6,}$", trimmed):
        return True
    return False
