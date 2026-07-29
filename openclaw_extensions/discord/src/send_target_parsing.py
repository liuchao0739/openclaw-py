import re
from typing import Any, Dict, Optional


class SendDiscordTarget:
    def __init__(self, kind: str, id: str, raw: str = ""):
        self.kind = kind
        self.id = id
        self.raw = raw or f"{kind}:{id}"


def parse_discord_send_target(raw: str, options: Optional[Dict[str, Any]] = None) -> Optional[SendDiscordTarget]:
    from .target_parsing import parse_discord_target

    target = parse_discord_target(raw, options or {})
    if not target:
        return None
    return SendDiscordTarget(
        kind=target["kind"], id=target["id"], raw=target["raw"]
    )
