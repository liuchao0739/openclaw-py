"""Discord API module exposes the plugin public contract."""

from __future__ import annotations

from importlib import import_module
from typing import Any


async def handle_discord_message_action(*args: Any, **kwargs: Any) -> Any:
    module = import_module("openclaw_extensions.discord.src.channel_actions_runtime")
    return await module.handle_discord_message_action(*args, **kwargs)


__all__ = ["handle_discord_message_action"]
