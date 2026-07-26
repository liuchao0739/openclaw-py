"""Feishu plugin module implements targets behavior."""

from __future__ import annotations

import re
from typing import Literal

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

FeishuIdType = Literal["chat_id", "open_id", "user_id"]

CHAT_ID_PREFIX = "oc_"
OPEN_ID_PREFIX = "ou_"
USER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def _strip_provider_prefix(raw: str) -> str:
    return re.sub(r"^(feishu|lark):", "", raw, flags=re.IGNORECASE).strip()


def detect_id_type(id_value: str) -> FeishuIdType | None:
    trimmed = id_value.strip()
    if trimmed.startswith(CHAT_ID_PREFIX):
        return "chat_id"
    if trimmed.startswith(OPEN_ID_PREFIX):
        return "open_id"
    if USER_ID_REGEX.fullmatch(trimmed):
        return "user_id"
    return None


def normalize_feishu_target(raw: str) -> str | None:
    trimmed = raw.strip()
    if not trimmed:
        return None

    without_provider = _strip_provider_prefix(trimmed)
    lowered = normalize_lowercase_string_or_empty(without_provider)
    if lowered.startswith("chat:"):
        return without_provider[len("chat:") :].strip() or None
    if lowered.startswith("group:"):
        return without_provider[len("group:") :].strip() or None
    if lowered.startswith("channel:"):
        return without_provider[len("channel:") :].strip() or None
    if lowered.startswith("user:"):
        return without_provider[len("user:") :].strip() or None
    if lowered.startswith("dm:"):
        return without_provider[len("dm:") :].strip() or None
    if lowered.startswith("open_id:"):
        return without_provider[len("open_id:") :].strip() or None

    return without_provider


def resolve_receive_id_type(id_value: str) -> FeishuIdType:
    trimmed = id_value.strip()
    lowered = normalize_lowercase_string_or_empty(trimmed)
    if lowered.startswith(("chat:", "group:", "channel:")):
        return "chat_id"
    if lowered.startswith("open_id:"):
        return "open_id"
    if lowered.startswith(("user:", "dm:")):
        normalized = re.sub(r"^(user|dm):", "", trimmed, flags=re.IGNORECASE).strip()
        return "open_id" if normalized.startswith(OPEN_ID_PREFIX) else "user_id"
    if trimmed.startswith(CHAT_ID_PREFIX):
        return "chat_id"
    if trimmed.startswith(OPEN_ID_PREFIX):
        return "open_id"
    return "user_id"


def looks_like_feishu_id(raw: str) -> bool:
    trimmed = _strip_provider_prefix(raw.strip())
    if not trimmed:
        return False
    if re.match(r"^(chat|group|channel|user|dm|open_id):", trimmed, flags=re.IGNORECASE):
        return True
    if trimmed.startswith(CHAT_ID_PREFIX):
        return True
    return trimmed.startswith(OPEN_ID_PREFIX)


__all__ = [
    "FeishuIdType",
    "detect_id_type",
    "looks_like_feishu_id",
    "normalize_feishu_target",
    "resolve_receive_id_type",
]
