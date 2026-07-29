from .target_parsing import parse_discord_target, resolve_discord_channel_id
from .target_resolver import resolve_discord_target


DiscordTarget = dict
DiscordTargetKind = str
DiscordTargetParseOptions = dict

__all__ = [
    "parse_discord_target",
    "resolve_discord_channel_id",
    "resolve_discord_target",
    "DiscordTarget",
    "DiscordTargetKind",
    "DiscordTargetParseOptions",
]
