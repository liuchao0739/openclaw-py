from __future__ import annotations

import json
import os
from typing import Any


async def onboard_config_write(
    config: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> str:
    rt = runtime or {}
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    if rt.get("log"):
        rt["log"](f"Config written to: {config_path}")
    return config_path
