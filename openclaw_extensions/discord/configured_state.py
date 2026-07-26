"""Discord helper module supports configured state behavior."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def has_discord_configured_state(params: dict[str, Any] | None = None) -> bool:
    env = (params or {}).get("env")
    if env is None:
        env = os.environ
    if not isinstance(env, Mapping):
        return False
    token = env.get("DISCORD_BOT_TOKEN")
    return isinstance(token, str) and token.strip() != ""


__all__ = ["has_discord_configured_state"]
