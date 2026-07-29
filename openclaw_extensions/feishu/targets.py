import re
from typing import Optional

from .types import FeishuIdType


_CHAT_ID_PREFIX = "oc_"
_OPEN_ID_PREFIX = "ou_"
_USER_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _strip_provider_prefix(raw: str) -> str:
    return re.sub(r"^(feishu|lark):", "", raw, flags=re.IGNORECASE).strip()


def _normalize_lower(value: str) -> str:
    return value.strip().lower()


def detect_id_type(id_value: str) -> Optional[FeishuIdType]:
    trimmed = id_value.strip()
    if trimmed.startswith(_CHAT_ID_PREFIX):
        return "chat_id"
    if trimmed.startswith(_OPEN_ID_PREFIX):
        return "open_id"
    if _USER_ID_RE.match(trimmed):
        return "user_id"
    return None


def normalize_feishu_target(raw: str) -> Optional[str]:
    trimmed = raw.strip()
    if not trimmed:
        return None
    without_provider = _strip_provider_prefix(trimmed)
    lowered = _normalize_lower(without_provider)
    for prefix in ["chat:", "group:", "channel:", "user:", "dm:", "open_id:"]:
        if lowered.startswith(prefix):
            return without_provider[len(prefix):].strip() or None
    return without_provider


def resolve_receive_id_type(id_value: str) -> str:
    trimmed = id_value.strip()
    lowered = _normalize_lower(trimmed)
    if lowered.startswith("chat:") or lowered.startswith("group:") or lowered.startswith("channel:"):
        return "chat_id"
    if lowered.startswith("open_id:"):
        return "open_id"
    if lowered.startswith("user:") or lowered.startswith("dm:"):
        normalized = re.sub(r"^(user|dm):", "", trimmed, flags=re.IGNORECASE).strip()
        return "open_id" if normalized.startswith(_OPEN_ID_PREFIX) else "user_id"
    if trimmed.startswith(_CHAT_ID_PREFIX):
        return "chat_id"
    if trimmed.startswith(_OPEN_ID_PREFIX):
        return "open_id"
    return "user_id"


def looks_like_feishu_id(raw: str) -> bool:
    trimmed = _strip_provider_prefix(raw.strip())
    if not trimmed:
        return False
    if re.match(r"^(chat|group|channel|user|dm|open_id):", trimmed, re.IGNORECASE):
        return True
    if trimmed.startswith(_CHAT_ID_PREFIX):
        return True
    if trimmed.startswith(_OPEN_ID_PREFIX):
        return True
    return False
