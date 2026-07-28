from __future__ import annotations

import asyncio
import time
from typing import Any

from openclaw.plugin_sdk.channel_inbound import (
    record_channel_bot_pair_loop_and_check_suppression,
)
from openclaw.plugin_sdk.pair_loop_guard_runtime import merge_pair_loop_guard_config
from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty
from openclaw_extensions.googlechat.runtime_api import (
    OpenClawConfig,
    resolve_inbound_route_envelope_builder_with_runtime,
    resolve_webhook_path,
)
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.api import (
    download_google_chat_media,
    send_google_chat_message,
)
from openclaw_extensions.googlechat.src.approval_card_click import (
    maybe_handle_google_chat_approval_card_click,
)
from openclaw_extensions.googlechat.src.monitor_access import (
    apply_google_chat_inbound_access_policy,
)
from openclaw_extensions.googlechat.src.monitor_durable import (
    resolve_google_chat_durable_reply_options,
)
from openclaw_extensions.googlechat.src.monitor_reply_delivery import (
    deliver_google_chat_reply,
)
from openclaw_extensions.googlechat.src.monitor_routing import (
    register_google_chat_webhook_target,
    set_google_chat_webhook_event_processor,
)
from openclaw_extensions.googlechat.src.monitor_types import (
    GoogleChatMonitorOptions,
    GoogleChatRuntimeEnv,
    WebhookTarget,
)
from openclaw_extensions.googlechat.src.monitor_webhook import (
    warn_app_principal_misconfiguration,
)
from openclaw_extensions.googlechat.src.runtime import get_google_chat_runtime
from openclaw_extensions.googlechat.src.types import (
    GoogleChatAttachment,
    GoogleChatEvent,
    GoogleChatSpace,
)


def _log_verbose(core, runtime: GoogleChatRuntimeEnv, message: str) -> None:
    if core.logging.should_log_verbose():
        log_fn = runtime.get("log") if isinstance(runtime, dict) else getattr(runtime, "log", None)
        if log_fn:
            log_fn(f"[googlechat] {message}")


def _normalize_audience_type(value: str | None = None) -> str | None:
    normalized = normalize_lowercase_string_or_empty(value)
    if normalized in ("app-url", "app_url", "app"):
        return "app-url"
    if normalized in ("project-number", "project_number", "project"):
        return "project-number"
    return None


def _resolve_google_chat_timestamp_ms(event_time: str | None = None) -> float | None:
    if not event_time:
        return None
    import datetime
    try:
        dt = datetime.datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        return dt.timestamp() * 1000
    except (ValueError, OSError):
        return None


def _is_google_chat_group_space(space: GoogleChatSpace) -> bool:
    space_type = (space.get("spaceType") or "").upper()
    if space_type == "DIRECT_MESSAGE":
        return False
    if space_type in ("SPACE", "GROUP_CHAT"):
        return True
    return space.get("singleUserBotDm") is not True and (space.get("type") or "").upper() != "DM"


def _resolve_google_chat_bot_loop_protection(params: dict) -> dict | None:
    allow_bots = params.get("allowBots", False)
    is_bot_sender = params.get("isBotSender", False)
    sender_id = params.get("senderId", "")
    app_user_id = params.get("appUserId", "")
    if not allow_bots or not is_bot_sender or not sender_id or sender_id == app_user_id:
        return None
    return {
        "scopeId": params.get("accountId", ""),
        "conversationId": params.get("conversationId", ""),
        "senderId": sender_id,
        "receiverId": app_user_id,
        "config": params.get("config"),
        "defaultsConfig": params.get("defaultsConfig"),
        "defaultEnabled": True,
        "nowMs": _resolve_google_chat_timestamp_ms(params.get("eventTime")),
    }


def _resolve_google_chat_bot_loop_protection_config(params: dict) -> dict:
    return merge_pair_loop_guard_config(
        params.get("accountConfig"),
        params.get("groupConfig"),
    )


def _should_suppress_google_chat_bot_loop(params: dict) -> bool:
    bot_loop_protection = params.get("botLoopProtection")
    if not bot_loop_protection:
        return False
    bot_loop_result = record_channel_bot_pair_loop_and_check_suppression(bot_loop_protection)
    if not bot_loop_result.get("suppressed"):
        return False
    _log_verbose(
        params["core"],
        params["runtime"],
        f"skip bot-to-bot loop in {bot_loop_protection.get('conversationId', '')}",
    )
    return True


async def _process_google_chat_event(event: GoogleChatEvent, target: WebhookTarget) -> None:
    event_type = event.get("type") or event.get("eventType")
    if event_type == "CARD_CLICKED":
        await maybe_handle_google_chat_approval_card_click({"event": event, "target": target})
        return
    if event_type != "MESSAGE":
        return
    if not event.get("message") or not event.get("space"):
        return

    await _process_message_with_pipeline({
        "event": event,
        "account": target["account"],
        "config": target["config"],
        "runtime": target["runtime"],
        "core": target["core"],
        "statusSink": target.get("statusSink"),
        "mediaMaxMb": target.get("mediaMaxMb", 20),
    })


def _resolve_bot_display_name(params: dict) -> str:
    account_name = params.get("accountName")
    agent_id = params.get("agentId", "")
    config = params.get("config", {})
    if account_name and account_name.strip():
        return account_name.strip()
    agent = None
    for a in config.get("agents", {}).get("list", []):
        if a.get("id") == agent_id:
            agent = a
            break
    if agent and agent.get("name", "").strip():
        return agent["name"].strip()
    return "OpenClaw"


async def _process_message_with_pipeline(params: dict) -> None:
    event = params["event"]
    account = params["account"]
    config = params["config"]
    runtime = params["runtime"]
    core = params["core"]
    status_sink = params.get("statusSink")
    media_max_mb = params["mediaMaxMb"]

    space = event.get("space")
    message = event.get("message")
    if not space or not message:
        return

    space_id = space.get("name", "")
    if not space_id:
        return

    is_group = _is_google_chat_group_space(space)
    sender = message.get("sender") or event.get("user")
    sender_id = (sender or {}).get("name", "")
    sender_name = (sender or {}).get("displayName", "")
    sender_email = (sender or {}).get("email")
    is_bot_sender = ((sender or {}).get("type") or "").upper() == "BOT"
    app_user_id = account.config.get("botUser", "").strip() or "users/app"

    allow_bots = account.config.get("allowBots", False)
    if not allow_bots:
        if is_bot_sender:
            _log_verbose(core, runtime, f"skip bot-authored message ({sender_id or 'unknown'})")
            return
        if sender_id == "users/app":
            _log_verbose(core, runtime, "skip app-authored message")
            return

    message_text = (message.get("argumentText") or message.get("text") or "").strip()
    attachments = message.get("attachment", [])
    if not isinstance(attachments, list):
        attachments = []
    has_media = len(attachments) > 0
    raw_body = message_text or ("<media:attachment>" if has_media else "")
    if not raw_body:
        return

    access = await apply_google_chat_inbound_access_policy({
        "account": account,
        "config": config,
        "core": core,
        "space": space,
        "message": message,
        "isGroup": is_group,
        "senderId": sender_id,
        "senderName": sender_name,
        "senderEmail": sender_email,
        "rawBody": raw_body,
        "statusSink": status_sink,
        "logVerbose": lambda m: _log_verbose(core, runtime, m),
    })
    if not access.get("ok"):
        return

    command_authorized = access.get("commandAuthorized")
    effective_was_mentioned = access.get("effectiveWasMentioned")
    group_bot_loop_protection = access.get("groupBotLoopProtection")
    group_system_prompt = access.get("groupSystemPrompt")

    bot_loop_protection = _resolve_google_chat_bot_loop_protection({
        "allowBots": allow_bots,
        "isBotSender": is_bot_sender,
        "senderId": sender_id,
        "appUserId": app_user_id,
        "accountId": account.account_id,
        "conversationId": space_id,
        "config": _resolve_google_chat_bot_loop_protection_config({
            "accountConfig": account.config.get("botLoopProtection"),
            "groupConfig": group_bot_loop_protection,
        }),
        "defaultsConfig": config.get("channels", {}).get("defaults", {}).get("botLoopProtection"),
        "eventTime": event.get("eventTime"),
    })
    if _should_suppress_google_chat_bot_loop({
        "botLoopProtection": bot_loop_protection,
        "core": core,
        "runtime": runtime,
    }):
        return

    route_result = resolve_inbound_route_envelope_builder_with_runtime({
        "cfg": config,
        "channel": "googlechat",
        "accountId": account.account_id,
        "peer": {
            "kind": "group" if is_group else "direct",
            "id": space_id,
        },
        "runtime": core.channel,
        "sessionStore": config.get("session", {}).get("store"),
    })
    route = route_result.get("route")
    build_envelope = route_result.get("buildEnvelope")

    media_path = None
    media_type = None
    if len(attachments) > 0:
        first = attachments[0]
        attachment_data = await _download_attachment(first, account, media_max_mb, core)
        if attachment_data:
            media_path = attachment_data["path"]
            media_type = attachment_data.get("contentType")

    from_label = (
        space.get("displayName") or f"space:{space_id}"
        if is_group
        else sender_name or f"user:{sender_id}"
    )
    timestamp_ms = _resolve_google_chat_timestamp_ms(event.get("eventTime"))

    store_path, body = build_envelope({
        "channel": "Google Chat",
        "from": from_label,
        "timestamp": timestamp_ms,
        "body": raw_body,
    })

    reply_thread_name = message.get("thread", {}).get("name") if is_group else None

    ctx_payload = core.channel.inbound.build_context({
        "channel": "googlechat",
        "accountId": route["accountId"],
        "messageId": message.get("name"),
        "messageIdFull": message.get("name"),
        "timestamp": timestamp_ms,
        "from": f"googlechat:{sender_id}",
        "sender": {
            "id": sender_id,
            "name": sender_name or None,
            "username": sender_email,
        },
        "conversation": {
            "kind": "channel" if is_group else "direct",
            "id": space_id,
            "label": from_label,
        },
        "route": {
            "agentId": route["agentId"],
            "accountId": route["accountId"],
            "routeSessionKey": route["sessionKey"],
        },
        "reply": {
            "to": f"googlechat:{space_id}",
            "originatingTo": f"googlechat:{space_id}",
            "replyToId": reply_thread_name,
            "replyToIdFull": reply_thread_name,
        },
        "message": {
            "body": body,
            "bodyForAgent": raw_body,
            "rawBody": raw_body,
            "commandBody": raw_body,
        },
        "media": (
            [{"path": media_path, "url": media_path, "contentType": media_type}]
            if media_path or media_type
            else None
        ),
        "supplemental": {
            "groupSystemPrompt": group_system_prompt if is_group else None,
        },
        "extra": {
            "ChatType": "channel" if is_group else "direct",
            "WasMentioned": effective_was_mentioned if is_group else None,
            "CommandAuthorized": command_authorized,
            "GroupSubject": None,
            "GroupSpace": space.get("displayName") if is_group else None,
        },
    })

    typing_indicator = account.config.get("typingIndicator", "message")
    if typing_indicator == "reaction":
        runtime.get("error", lambda m: None)(
            f"[{account.account_id}] typingIndicator='reaction' requires user OAuth (not supported with service account). Falling back to 'message' mode."
        )
        typing_indicator = "message"
    typing_message_name = None

    if typing_indicator == "message":
        try:
            bot_name = _resolve_bot_display_name({
                "accountName": account.config.get("name"),
                "agentId": route["agentId"],
                "config": config,
            })
            result = await send_google_chat_message({
                "account": account,
                "space": space_id,
                "text": f"_{bot_name} is typing..._",
                "thread": reply_thread_name,
            })
            if result:
                typing_message_name = result.get("messageName")
        except Exception as err:
            runtime.get("error", lambda m: None)(f"Failed sending typing message: {err}")

    async def _ingest():
        return {
            "id": message.get("name") or space_id,
            "timestamp": timestamp_ms,
            "rawText": raw_body,
            "textForAgent": raw_body,
            "textForCommands": raw_body,
            "raw": message,
        }

    async def _resolve_turn():
        return {
            "cfg": config,
            "channel": "googlechat",
            "accountId": route["accountId"],
            "agentId": route["agentId"],
            "routeSessionKey": route["sessionKey"],
            "storePath": store_path,
            "ctxPayload": ctx_payload,
            "recordInboundSession": core.channel.session.record_inbound_session,
            "dispatchReplyWithBufferedBlockDispatcher": (
                core.channel.reply.dispatch_reply_with_buffered_block_dispatcher
            ),
        }

    async def _deliver(delivery_payload: dict, info: dict) -> None:
        durable = resolve_google_chat_durable_reply_options({
            "payload": delivery_payload,
            "infoKind": info.get("kind"),
            "spaceId": space_id,
            "typingMessageName": typing_message_name,
        })
        if durable:
            return

        nonlocal typing_message_name
        await deliver_google_chat_reply({
            "payload": delivery_payload,
            "account": account,
            "spaceId": space_id,
            "runtime": runtime,
            "core": core,
            "config": config,
            "statusSink": status_sink,
            "typingMessageName": typing_message_name,
        })
        typing_message_name = None

    async def _on_delivered() -> None:
        if status_sink:
            status_sink({"lastOutboundAt": time.time() * 1000})

    async def _on_error(err: Exception, info: dict) -> None:
        runtime.get("error", lambda m: None)(
            f"[{account.accountId}] Google Chat {info.get('kind')} reply failed: {err}"
        )

    await core.channel.inbound.run({
        "channel": "googlechat",
        "accountId": route["accountId"],
        "raw": message,
        "adapter": {
            "ingest": _ingest,
            "resolveTurn": _resolve_turn,
            "delivery": {
                "durable": lambda p, info: resolve_google_chat_durable_reply_options({
                    "payload": p,
                    "infoKind": info.get("kind"),
                    "spaceId": space_id,
                    "typingMessageName": typing_message_name,
                }),
                "deliver": _deliver,
                "onDelivered": _on_delivered,
                "onError": _on_error,
            },
            "replyPipeline": {},
            "record": {
                "onRecordError": lambda err: runtime.get("error", lambda m: None)(
                    f"googlechat: failed updating session meta: {err}"
                ),
            },
        },
    })


async def _download_attachment(
    attachment: GoogleChatAttachment,
    account: ResolvedGoogleChatAccount,
    media_max_mb: int,
    core,
) -> dict | None:
    resource_name = (attachment.get("attachmentDataRef") or {}).get("resourceName")
    if not resource_name:
        return None
    max_bytes = max(1, media_max_mb) * 1024 * 1024
    downloaded = await download_google_chat_media({
        "account": account,
        "resourceName": resource_name,
        "maxBytes": max_bytes,
    })
    saved = await core.channel.media.save_media_buffer(
        downloaded["buffer"],
        downloaded.get("contentType") or attachment.get("contentType"),
        "inbound",
        max_bytes,
        attachment.get("contentName"),
    )
    return {"path": saved["path"], "contentType": saved.get("contentType")}


set_google_chat_webhook_event_processor(_process_google_chat_event)


def _monitor_google_chat_provider(options: GoogleChatMonitorOptions):
    core = get_google_chat_runtime()
    webhook_path = resolve_webhook_path({
        "webhookPath": options.get("webhookPath"),
        "webhookUrl": options.get("webhookUrl"),
        "defaultPath": "/googlechat",
    })
    if not webhook_path:
        options["runtime"].get("error", lambda m: None)(
            f"[{options['account'].account_id}] invalid webhook path"
        )
        return lambda: None

    audience_type = _normalize_audience_type(options["account"].config.get("audienceType"))
    audience = options["account"].config.get("audience", "").strip()
    media_max_mb = options["account"].config.get("mediaMaxMb", 20)

    warn_app_principal_misconfiguration({
        "accountId": options["account"].account_id,
        "audienceType": audience_type,
        "appPrincipal": options["account"].config.get("appPrincipal"),
        "log": options["runtime"].get("log", lambda m: None),
    })

    unregister_target = register_google_chat_webhook_target({
        "account": options["account"],
        "config": options["config"],
        "runtime": options["runtime"],
        "core": core,
        "path": webhook_path,
        "audienceType": audience_type,
        "audience": audience,
        "statusSink": options.get("statusSink"),
        "mediaMaxMb": media_max_mb,
    })

    return unregister_target


async def start_google_chat_monitor(params: GoogleChatMonitorOptions):
    return _monitor_google_chat_provider(params)


def resolve_google_chat_webhook_path(params: dict) -> str:
    result = resolve_webhook_path({
        "webhookPath": params["account"].config.get("webhookPath"),
        "webhookUrl": params["account"].config.get("webhookUrl"),
        "defaultPath": "/googlechat",
    })
    return result or "/googlechat"


__all__ = [
    "start_google_chat_monitor",
    "resolve_google_chat_webhook_path",
    "testing",
]

testing = {
    "processMessageWithPipeline": _process_message_with_pipeline,
    "resolveGoogleChatBotLoopProtection": _resolve_google_chat_bot_loop_protection,
    "resolveGoogleChatBotLoopProtectionConfig": _resolve_google_chat_bot_loop_protection_config,
    "shouldSuppressGoogleChatBotLoop": _should_suppress_google_chat_bot_loop,
}