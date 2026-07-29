import re
from typing import Any, Optional


def normalize_explicit_discord_session_key(session_key: str, ctx: Optional[Any] = None) -> str:
    trimmed = (session_key or "").strip()
    if not trimmed:
        return trimmed
    normalized = re.sub(r"^discord:", "", trimmed, flags=re.I)
    return normalized or trimmed
