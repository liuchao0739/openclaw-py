from typing import Any, Dict, Optional

from .target_parsing import parse_discord_target


def resolve_discord_target(
    raw: str,
    ctx: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    target = parse_discord_target(raw, options or {})
    if not target:
        return None
    return {
        "kind": target["kind"],
        "id": target["id"],
        "raw": target["raw"],
        "normalized": target["normalized"],
    }
