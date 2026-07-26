"""Discord plugin module implements runtime.moderation shared behavior."""

from __future__ import annotations

from typing import Any, Literal

from openclaw.agents.tools.common import ToolInputError, read_string_param
from openclaw.plugin_sdk import read_non_negative_integer_param

DiscordModerationAction = Literal["timeout", "kick", "ban"]


def is_discord_moderation_action(action: str) -> bool:
    return action in ("timeout", "kick", "ban")


def read_discord_moderation_command(
    action: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    if not is_discord_moderation_action(action):
        raise ValueError(f"Unsupported Discord moderation action: {action}")
    duration_minutes = read_non_negative_integer_param(params, "durationMinutes")
    if duration_minutes is None and params.get("durationMinutes") is not None:
        raise ToolInputError("durationMinutes must be a non-negative integer")
    delete_message_days = read_non_negative_integer_param(params, "deleteMessageDays")
    if delete_message_days is None and params.get("deleteMessageDays") is not None:
        raise ToolInputError("deleteMessageDays must be an integer from 0 to 7")
    if delete_message_days is not None and delete_message_days > 7:
        raise ToolInputError("deleteMessageDays must be an integer from 0 to 7")
    return {
        "action": action,
        "guildId": read_string_param(params, "guildId", required=True),
        "userId": read_string_param(params, "userId", required=True),
        "durationMinutes": duration_minutes,
        "until": read_string_param(params, "until"),
        "reason": read_string_param(params, "reason"),
        "deleteMessageDays": delete_message_days,
    }


__all__ = ["is_discord_moderation_action", "read_discord_moderation_command"]
