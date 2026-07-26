"""Discord plugin module implements handle action behavior."""

from __future__ import annotations

from typing import Any

from openclaw.agents.tools.common import (
    read_boolean_param,
    read_positive_integer_param,
    read_string_param,
)
from openclaw.channels.plugins.actions import resolve_reaction_message_id
from openclaw.packages.normalization_core import normalize_optional_stringified_id
from openclaw.plugin_sdk import read_string_array_param
from openclaw_extensions.discord.action_runtime_api import handle_discord_action
from openclaw_extensions.discord.src.actions.handle_action_guild_admin import (
    try_handle_discord_message_action_guild_admin,
)
from openclaw_extensions.discord.src.inbound_event_delivery import (
    notify_discord_inbound_event_outbound_success,
)
from openclaw_extensions.discord.src.shared_interactive import (
    build_discord_interactive_components,
    build_discord_presentation_components,
    normalize_interactive_reply,
    normalize_message_presentation,
)
from openclaw_extensions.discord.src.targets import resolve_discord_channel_id

_PROVIDER_ID = "discord"


def _read_current_discord_target(tool_context: dict[str, Any] | None) -> str | None:
    provider = str((tool_context or {}).get("currentChannelProvider") or "").strip().lower()
    if provider and provider != _PROVIDER_ID:
        return None
    target = str((tool_context or {}).get("currentChannelId") or "").strip()
    return target or None


async def handle_discord_message_action(ctx: dict[str, Any]) -> dict[str, Any]:
    action = ctx["action"]
    params = ctx["params"]
    cfg = ctx["cfg"]
    account_id = ctx.get("accountId") or read_string_param(params, "accountId")
    action_options = {
        "mediaAccess": ctx.get("mediaAccess"),
        "mediaLocalRoots": ctx.get("mediaLocalRoots"),
        "mediaReadFile": ctx.get("mediaReadFile"),
    }

    def notify_visible_outbound(to: str, fallback_session_key: str | None = None) -> None:
        notify_discord_inbound_event_outbound_success(
            {
                "sessionKey": ctx.get("sessionKey") or fallback_session_key,
                "to": to,
                "accountId": account_id,
                "inboundEventKind": ctx.get("inboundEventKind"),
            }
        )

    def read_target() -> str:
        target = (
            read_string_param(params, "channelId")
            or read_string_param(params, "to")
            or _read_current_discord_target(ctx.get("toolContext"))
        )
        if not target:
            raise ValueError("Discord channel target is required (use channel:<id>).")
        return target

    def resolve_channel_id() -> str:
        return resolve_discord_channel_id(read_target())

    def read_send_target() -> str:
        target = (
            read_string_param(params, "to")
            or read_string_param(params, "target")
            or _read_current_discord_target(ctx.get("toolContext"))
        )
        if not target:
            raise ValueError("Discord channel target is required (use channel:<id>).")
        return target

    if action == "send":
        to = read_send_target()
        as_voice = read_boolean_param(params, "asVoice") is True
        raw_components = (
            params.get("components")
            or build_discord_presentation_components(
                normalize_message_presentation(params.get("presentation"))
            )
            or build_discord_interactive_components(
                normalize_interactive_reply(params.get("interactive"))
            )
        )
        has_components = bool(raw_components) and (
            callable(raw_components) or isinstance(raw_components, dict)
        )
        components = raw_components if has_components else None
        media_url = (
            read_string_param(params, "media", trim=False)
            or read_string_param(params, "path", trim=False)
            or read_string_param(params, "filePath", trim=False)
        )
        content = read_string_param(
            params,
            "message",
            required=not as_voice and not has_components and not media_url,
            allow_empty=True,
        )
        filename = read_string_param(params, "filename")
        reply_to = read_string_param(params, "replyTo")
        raw_embeds = params.get("embeds")
        embeds = raw_embeds if isinstance(raw_embeds, list) else None
        silent = read_boolean_param(params, "silent") is True
        suppress_embeds = read_boolean_param(params, "suppressEmbeds")
        session_key = read_string_param(params, "__sessionKey")
        agent_id = read_string_param(params, "__agentId")
        thread_name = read_string_param(params, "threadName")
        payload: dict[str, Any] = {
            "action": "sendMessage",
            "accountId": account_id,
            "to": to,
            "content": content or "",
            "mediaUrl": media_url,
            "filename": filename,
            "replyTo": reply_to,
            "components": components,
            "embeds": embeds,
            "asVoice": as_voice,
            "silent": silent,
            "__sessionKey": session_key,
            "__agentId": agent_id,
        }
        if thread_name:
            payload["threadName"] = thread_name
        if suppress_embeds is not None:
            payload["suppressEmbeds"] = suppress_embeds
        result = await handle_discord_action(payload, cfg, action_options)
        notify_visible_outbound(to, session_key)
        return result

    if action == "upload-file":
        to = read_send_target()
        media_url = (
            read_string_param(params, "filePath", trim=False)
            or read_string_param(params, "path", trim=False)
            or read_string_param(params, "media", trim=False)
        )
        if not media_url:
            raise ValueError("upload-file requires filePath, path, or media.")
        content = read_string_param(params, "message", allow_empty=True) or read_string_param(
            params,
            "content",
            allow_empty=True,
        )
        filename = read_string_param(params, "filename")
        reply_to = read_string_param(params, "replyTo")
        silent = read_boolean_param(params, "silent") is True
        suppress_embeds = read_boolean_param(params, "suppressEmbeds")
        session_key = read_string_param(params, "__sessionKey")
        agent_id = read_string_param(params, "__agentId")
        payload = {
            "action": "sendMessage",
            "accountId": account_id,
            "to": to,
            "content": content or "",
            "mediaUrl": media_url,
            "filename": filename,
            "replyTo": reply_to,
            "silent": silent,
            "__sessionKey": session_key,
            "__agentId": agent_id,
        }
        if suppress_embeds is not None:
            payload["suppressEmbeds"] = suppress_embeds
        result = await handle_discord_action(payload, cfg, action_options)
        notify_visible_outbound(to, session_key)
        return result

    if action == "poll":
        to = read_string_param(params, "to", required=True)
        question = read_string_param(params, "pollQuestion", required=True)
        answers = read_string_array_param(params, "pollOption")
        if not answers:
            raise ValueError("pollOption required")
        allow_multiselect = read_boolean_param(params, "pollMulti")
        duration_hours = read_positive_integer_param(params, "pollDurationHours")
        result = await handle_discord_action(
            {
                "action": "poll",
                "accountId": account_id,
                "to": to,
                "question": question,
                "answers": answers,
                "allowMultiselect": allow_multiselect,
                "durationHours": duration_hours,
                "content": read_string_param(params, "message"),
            },
            cfg,
            action_options,
        )
        notify_visible_outbound(to)
        return result

    if action == "react":
        message_id_raw = resolve_reaction_message_id(params, ctx.get("toolContext"))
        message_id = normalize_optional_stringified_id(message_id_raw) or ""
        if not message_id:
            raise ValueError(
                "messageId required. Provide messageId explicitly or react to the current inbound message."
            )
        emoji = read_string_param(params, "emoji", allow_empty=True)
        remove = read_boolean_param(params, "remove")
        return await handle_discord_action(
            {
                "action": "react",
                "accountId": account_id,
                "channelId": read_target(),
                "messageId": message_id,
                "emoji": emoji,
                "remove": remove,
            },
            cfg,
            action_options,
        )

    if action == "reactions":
        message_id = read_string_param(params, "messageId", required=True)
        limit = read_positive_integer_param(params, "limit")
        return await handle_discord_action(
            {
                "action": "reactions",
                "accountId": account_id,
                "channelId": read_target(),
                "messageId": message_id,
                "limit": limit,
            },
            cfg,
            action_options,
        )

    if action == "read":
        limit = read_positive_integer_param(params, "limit")
        return await handle_discord_action(
            {
                "action": "readMessages",
                "accountId": account_id,
                "channelId": resolve_channel_id(),
                "limit": limit,
                "before": read_string_param(params, "before"),
                "after": read_string_param(params, "after"),
                "around": read_string_param(params, "around"),
            },
            cfg,
            action_options,
        )

    if action == "edit":
        message_id = read_string_param(params, "messageId", required=True)
        content = read_string_param(params, "message", required=True)
        return await handle_discord_action(
            {
                "action": "editMessage",
                "accountId": account_id,
                "channelId": resolve_channel_id(),
                "messageId": message_id,
                "content": content,
            },
            cfg,
            action_options,
        )

    if action == "delete":
        message_id = read_string_param(params, "messageId", required=True)
        return await handle_discord_action(
            {
                "action": "deleteMessage",
                "accountId": account_id,
                "channelId": resolve_channel_id(),
                "messageId": message_id,
            },
            cfg,
            action_options,
        )

    if action in ("pin", "unpin", "list-pins"):
        message_id = (
            None
            if action == "list-pins"
            else read_string_param(params, "messageId", required=True)
        )
        mapped_action = {
            "pin": "pinMessage",
            "unpin": "unpinMessage",
            "list-pins": "listPins",
        }[action]
        return await handle_discord_action(
            {
                "action": mapped_action,
                "accountId": account_id,
                "channelId": resolve_channel_id(),
                "messageId": message_id,
            },
            cfg,
            action_options,
        )

    if action == "permissions":
        return await handle_discord_action(
            {
                "action": "permissions",
                "accountId": account_id,
                "channelId": resolve_channel_id(),
            },
            cfg,
            action_options,
        )

    if action == "thread-create":
        name = read_string_param(params, "threadName", required=True)
        message_id = read_string_param(params, "messageId")
        content = read_string_param(params, "message")
        auto_archive_minutes = read_positive_integer_param(params, "autoArchiveMin")
        applied_tags = read_string_array_param(params, "appliedTags")
        result = await handle_discord_action(
            {
                "action": "threadCreate",
                "accountId": account_id,
                "channelId": resolve_channel_id(),
                "name": name,
                "messageId": message_id,
                "content": content,
                "autoArchiveMinutes": auto_archive_minutes,
                "appliedTags": applied_tags,
            },
            cfg,
            action_options,
        )
        notify_visible_outbound(resolve_channel_id())
        return result

    if action == "sticker":
        to = read_string_param(params, "to", required=True)
        sticker_ids = read_string_array_param(params, "stickerId")
        if not sticker_ids:
            raise ValueError("sticker-id required")
        result = await handle_discord_action(
            {
                "action": "sticker",
                "accountId": account_id,
                "to": to,
                "stickerIds": sticker_ids,
                "content": read_string_param(params, "message"),
            },
            cfg,
            action_options,
        )
        notify_visible_outbound(to)
        return result

    if action == "set-presence":
        return await handle_discord_action(
            {
                "action": "setPresence",
                "accountId": account_id,
                "status": read_string_param(params, "status"),
                "activityType": read_string_param(params, "activityType"),
                "activityName": read_string_param(params, "activityName"),
                "activityUrl": read_string_param(params, "activityUrl"),
                "activityState": read_string_param(params, "activityState"),
            },
            cfg,
            action_options,
        )

    admin_result = await try_handle_discord_message_action_guild_admin(
        ctx=ctx,
        resolve_channel_id=resolve_channel_id,
    )
    if admin_result is not None:
        if action == "thread-reply":
            notify_visible_outbound(
                read_string_param(params, "threadId") or read_target()
            )
        return admin_result

    raise ValueError(f"Action {action} is not supported for provider {_PROVIDER_ID}.")


__all__ = ["handle_discord_message_action"]
