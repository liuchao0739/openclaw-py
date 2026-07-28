from __future__ import annotations

from typing import Any


def resolve_agent_settings(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    return {
        "maxTurns": config.get("maxTurns", 50),
        "compactionEnabled": config.get("compactionEnabled", True),
        "streamingEnabled": config.get("streamingEnabled", True),
        "thinkingEnabled": config.get("thinkingEnabled", True),
        "toolUseEnabled": config.get("toolUseEnabled", True),
    }
