"""Defines channel bot-loop protection configuration types."""

from typing import TypedDict


class ChannelBotLoopProtectionConfig(TypedDict, total=False):
    """Configuration for channel bot-loop protection."""

    enabled: bool
    max_events_per_window: int
    window_seconds: int
    cooldown_seconds: int
