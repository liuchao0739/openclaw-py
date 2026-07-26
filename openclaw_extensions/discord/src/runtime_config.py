"""Discord helper module supports runtime config behavior."""

from __future__ import annotations

from typing import Any


def select_discord_runtime_config(input_config: dict[str, Any]) -> dict[str, Any]:
    return input_config


__all__ = ["select_discord_runtime_config"]
