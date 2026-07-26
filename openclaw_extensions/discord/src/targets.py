"""Discord plugin module implements targets behavior."""

from __future__ import annotations

from openclaw_extensions.discord.src.target_parsing import (
    DiscordTarget,
    DiscordTargetKind,
    parse_discord_target,
    resolve_discord_channel_id,
)

__all__ = [
    "DiscordTarget",
    "DiscordTargetKind",
    "parse_discord_target",
    "resolve_discord_channel_id",
]
