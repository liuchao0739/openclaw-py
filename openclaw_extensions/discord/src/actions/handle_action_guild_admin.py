"""Discord plugin module implements handle action.guild admin behavior."""

from __future__ import annotations

from typing import Any

from openclaw.agents.tools.common import (
    ToolInputError,
    _read_param_raw,
    read_positive_integer_param,
    read_string_param,
)
from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugin_sdk import read_string_array_param
from openclaw_extensions.discord.action_runtime_api import handle_discord_action
from openclaw_extensions.discord.src.actions.runtime_moderation_shared import (
    is_discord_moderation_action,
    read_discord_moderation_command,
)
from openclaw_extensions.discord.src.trusted_requester_actions import (
    is_trusted_requester_guild_admin_action,
)


def _read_strict_non_negative_integer_param(
    params: dict[str, Any],
    key: str,
    *,
    message: str | None = None,
    max_value: int | None = None,
) -> int | None:
    raw = _read_param_raw(params, key)
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw != int(raw) or raw < 0:
        raise ToolInputError(message or f"{key} must be a non-negative integer")
    value = int(raw)
    if max_value is not None and value > max_value:
        raise ToolInputError(message or f"{key} must be a non-negative integer")
    return value


def _read_discord_requester_sender_id(ctx: dict[str, Any]) -> str | None:
    tool_context = ctx.get("toolContext") or {}
    current_provider = normalize_optional_string(tool_context.get("currentChannelProvider"))
    if current_provider and current_provider.lower() == "discord":
        return normalize_optional_string(ctx.get("requesterSenderId"))
    action = ctx.get("action")
    if is_trusted_requester_guild_admin_action(str(action)) and (
        current_provider or ctx.get("senderIsOwner") is not True
    ):
        raise ValueError("Discord guild admin actions require a trusted Discord sender identity.")
    return None


def _sender_param(sender_user_id: str | None) -> dict[str, str]:
    return {"senderUserId": sender_user_id} if sender_user_id else {}


async def try_handle_discord_message_action_guild_admin(
    *,
    ctx: dict[str, Any],
    resolve_channel_id: Any,
) -> dict[str, Any] | None:
    action = ctx["action"]
    action_params = ctx["params"]
    cfg = ctx["cfg"]
    account_id = ctx.get("accountId") or read_string_param(action_params, "accountId")
    sender_user_id = _read_discord_requester_sender_id(ctx)

    if action == "member-info":
        return await handle_discord_action(
            {
                "action": "memberInfo",
                "accountId": account_id,
                "guildId": read_string_param(action_params, "guildId", required=True),
                "userId": read_string_param(action_params, "userId", required=True),
            },
            cfg,
        )

    if action == "role-info":
        return await handle_discord_action(
            {
                "action": "roleInfo",
                "accountId": account_id,
                "guildId": read_string_param(action_params, "guildId", required=True),
            },
            cfg,
        )

    if action == "emoji-list":
        return await handle_discord_action(
            {
                "action": "emojiList",
                "accountId": account_id,
                "guildId": read_string_param(action_params, "guildId", required=True),
            },
            cfg,
        )

    if action == "channel-info":
        return await handle_discord_action(
            {
                "action": "channelInfo",
                "accountId": account_id,
                "channelId": read_string_param(action_params, "channelId", required=True),
            },
            cfg,
        )

    if action == "channel-delete":
        return await handle_discord_action(
            {
                "action": "channelDelete",
                "accountId": account_id,
                "channelId": read_string_param(action_params, "channelId", required=True),
                **_sender_param(sender_user_id),
            },
            cfg,
        )

    if is_discord_moderation_action(action):
        moderation = read_discord_moderation_command(
            action,
            {
                **action_params,
                "durationMinutes": _read_strict_non_negative_integer_param(
                    action_params,
                    "durationMin",
                ),
                "deleteMessageDays": _read_strict_non_negative_integer_param(
                    action_params,
                    "deleteDays",
                    message="deleteDays must be an integer from 0 to 7",
                    max_value=7,
                ),
            },
        )
        return await handle_discord_action(
            {
                "action": moderation["action"],
                "accountId": account_id,
                "guildId": moderation["guildId"],
                "userId": moderation["userId"],
                "durationMinutes": moderation.get("durationMinutes"),
                "until": moderation.get("until"),
                "reason": moderation.get("reason"),
                "deleteMessageDays": moderation.get("deleteMessageDays"),
                "senderUserId": sender_user_id,
            },
            cfg,
        )

    if action == "thread-reply":
        content = read_string_param(action_params, "message", required=True)
        media_url = (
            read_string_param(action_params, "media", trim=False)
            or read_string_param(action_params, "path", trim=False)
            or read_string_param(action_params, "filePath", trim=False)
        )
        reply_to = read_string_param(action_params, "replyTo")
        thread_id = read_string_param(action_params, "threadId")
        channel_id = thread_id or resolve_channel_id()
        return await handle_discord_action(
            {
                "action": "threadReply",
                "accountId": account_id,
                "channelId": channel_id,
                "content": content,
                "mediaUrl": media_url,
                "replyTo": reply_to,
            },
            cfg,
            {
                "mediaLocalRoots": ctx.get("mediaLocalRoots"),
                "mediaReadFile": ctx.get("mediaReadFile"),
            },
        )

    if action == "search":
        guild_id = read_string_param(action_params, "guildId")
        query = read_string_param(action_params, "query") or read_string_param(
            action_params,
            "content",
        )
        if not query:
            raise ValueError("Discord search requires query text. Provide query or content.")
        explicit_channel_ids = read_string_array_param(action_params, "channelIds")
        tool_context = ctx.get("toolContext") or {}
        channel_id = read_string_param(action_params, "channelId")
        if (
            channel_id is None
            and not guild_id
            and not explicit_channel_ids
            and str(tool_context.get("currentChannelProvider") or "").strip().lower() == "discord"
        ):
            channel_id = str(tool_context.get("currentChannelId") or "").strip() or None
        payload: dict[str, Any] = {
            "action": "searchMessages",
            "accountId": account_id,
            "content": query,
            "authorId": read_string_param(action_params, "authorId"),
            "authorIds": read_string_array_param(action_params, "authorIds"),
            "limit": read_positive_integer_param(action_params, "limit"),
        }
        if guild_id:
            payload["guildId"] = guild_id
        if channel_id:
            payload["channelId"] = channel_id
        if explicit_channel_ids:
            payload["channelIds"] = explicit_channel_ids
        return await handle_discord_action(payload, cfg)

    return None


__all__ = ["try_handle_discord_message_action_guild_admin"]
