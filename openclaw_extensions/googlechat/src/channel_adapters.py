from __future__ import annotations

from openclaw.plugin_sdk.channel_config_helpers import adapt_scoped_account_accessor
from openclaw.plugin_sdk.channel_outbound import (
    create_message_receipt_from_outbound_results,
    define_channel_message_adapter,
    sanitize_for_plain_text,
)
from openclaw.plugin_sdk.channel_policy import (
    compose_account_warning_collectors,
    create_allowlist_provider_open_warning_collector,
)
from openclaw.plugin_sdk.directory_runtime import (
    create_channel_directory_adapter,
    list_resolved_directory_group_entries_from_map_keys,
    list_resolved_directory_user_entries_from_allow_from,
)
from openclaw.plugin_sdk.lazy_runtime import create_lazy_runtime_named_export
from openclaw.plugin_sdk.string_coerce_runtime import normalize_optional_string
from openclaw.plugin_sdk.text_chunking import sanitize_assistant_visible_text
from openclaw_extensions.googlechat.src.approval_card_actions import (
    should_suppress_google_chat_manual_exec_approval_followup_payload,
)
from openclaw_extensions.googlechat.src.channel_base import (
    format_google_chat_allow_from_entry,
)
from openclaw_extensions.googlechat.src.channel_deps_runtime import (
    DEFAULT_ACCOUNT_ID,
    GoogleChatConfigSchema,
    OpenClawConfig,
    ResolvedGoogleChatAccount,
    chunk_text_for_outbound,
    is_google_chat_user_target,
    load_outbound_media_from_url,
    missing_target_error,
    normalize_google_chat_target,
    read_remote_media_buffer,
    resolve_channel_media_max_bytes,
    resolve_google_chat_account,
    resolve_google_chat_outbound_space,
)
from openclaw_extensions.googlechat.src.group_policy import (
    resolve_google_chat_group_require_mention,
)

load_google_chat_channel_runtime = create_lazy_runtime_named_export(
    lambda: __import__(
        "openclaw_extensions.googlechat.src.channel_runtime",
        fromlist=["google_chat_channel_runtime"],
    ),
    "googleChatChannelRuntime",
)

PAIRING_APPROVED_MESSAGE = "Your Google Chat account is paired and ready."


def _create_google_chat_send_receipt(params: dict) -> dict:
    message_id = normalize_optional_string(params.get("messageId", ""))
    return create_message_receipt_from_outbound_results({
        "results": (
            [{
                "channel": "googlechat",
                "messageId": message_id,
                "chatId": params["chatId"],
                "conversationId": params["chatId"],
            }]
            if message_id
            else []
        ),
        "threadId": params["chatId"],
        "kind": params["kind"],
    })


_collect_google_chat_group_policy_warning = create_allowlist_provider_open_warning_collector(
    provider_config_present=lambda cfg: (cfg.get("channels") or {}).get("googlechat") is not None,
    resolve_group_policy=lambda account: (account.config.get("groupPolicy")),
    build_open_warning={
        "surface": "Google Chat spaces",
        "openBehavior": "allows any space to trigger (mention-gated)",
        "remediation": (
            'Set channels.googlechat.groupPolicy="allowlist" and configure channels.googlechat.groups'
        ),
    },
)


def _collect_google_chat_dm_open_warning(account: ResolvedGoogleChatAccount) -> str | None:
    dm_policy = (account.config.get("dm") or {}).get("policy")
    if dm_policy == "open":
        return '- Google Chat DMs are open to anyone. Set channels.googlechat.dm.policy="pairing" or "allowlist".'
    return None


_collect_google_chat_security_warnings = compose_account_warning_collectors(
    _collect_google_chat_group_policy_warning,
    _collect_google_chat_dm_open_warning,
)


googlechat_groups_adapter = {
    "resolveRequireMention": resolve_google_chat_group_require_mention,
}


async def _list_peers(params: dict) -> list:
    return list_resolved_directory_user_entries_from_allow_from({
        **params,
        "resolve_account": adapt_scoped_account_accessor(
            lambda p: resolve_google_chat_account(cfg=p["cfg"], account_id=p.get("accountId"))
        ),
        "resolve_allow_from": lambda account: (account.config.get("dm") or {}).get("allowFrom"),
        "normalize_id": lambda entry: normalize_google_chat_target(entry) or entry,
    })


async def _list_groups(params: dict) -> list:
    return list_resolved_directory_group_entries_from_map_keys({
        **params,
        "resolve_account": adapt_scoped_account_accessor(
            lambda p: resolve_google_chat_account(cfg=p["cfg"], account_id=p.get("accountId"))
        ),
        "resolve_groups": lambda account: account.config.get("groups"),
    })


googlechat_directory_adapter = create_channel_directory_adapter(
    list_peers=_list_peers,
    list_groups=_list_groups,
)

googlechat_security_adapter = {
    "dm": {
        "channelKey": "googlechat",
        "resolvePolicy": lambda account: (account.config.get("dm") or {}).get("policy"),
        "resolveAllowFrom": lambda account: (account.config.get("dm") or {}).get("allowFrom"),
        "allowFromPathSuffix": "dm.",
        "normalizeEntry": lambda raw: format_google_chat_allow_from_entry(raw),
    },
    "collectWarnings": _collect_google_chat_security_warnings,
}


googlechat_threading_adapter = {
    "scopedAccountReplyToMode": {
        "resolveAccount": lambda cfg, account_id: resolve_google_chat_account(cfg=cfg, account_id=account_id),
        "resolveReplyToMode": lambda account, chat_type: account.config.get("replyToMode"),
        "fallback": "off",
    },
    "buildToolContext": lambda params: {
        "currentChannelId": normalize_google_chat_target(params["context"]["To"]),
        "currentMessageId": normalize_optional_string(params["context"].get("ReplyToIdFull"))
        or normalize_optional_string(params["context"].get("ReplyToId")),
        "currentThreadTs": normalize_optional_string(params["context"].get("ReplyToIdFull"))
        or normalize_optional_string(params["context"].get("ReplyToId")),
        "replyToMode": resolve_google_chat_account(
            cfg=params["cfg"],
            account_id=params.get("accountId"),
        ).config.get("replyToMode"),
        "hasRepliedRef": params.get("hasRepliedRef"),
    },
}


async def _pairing_notify(params: dict) -> None:
    account = resolve_google_chat_account(cfg=params["cfg"], account_id=params.get("accountId"))
    if account.credential_source == "none":
        return
    user = normalize_google_chat_target(params["id"]) or params["id"]
    target = user if is_google_chat_user_target(user) else f"users/{user}"
    space = await resolve_google_chat_outbound_space({"account": account, "target": target})
    runtime = load_google_chat_channel_runtime()
    send_fn = runtime["sendGoogleChatMessage"]
    await send_fn({"account": account, "space": space, "text": params["message"]})


googlechat_pairing_text_adapter = {
    "idLabel": "googlechatUserId",
    "message": PAIRING_APPROVED_MESSAGE,
    "normalizeAllowEntry": lambda entry: format_google_chat_allow_from_entry(entry),
    "notify": _pairing_notify,
}


def _sanitize_text(params: dict) -> str:
    return sanitize_for_plain_text(sanitize_assistant_visible_text(params["text"]))


def _normalize_payload(params: dict) -> dict | None:
    if should_suppress_google_chat_manual_exec_approval_followup_payload(params["payload"]):
        return None
    return params["payload"]


def _resolve_target(params: dict) -> dict:
    to = normalize_optional_string(params.get("to")) or ""
    if to:
        normalized = normalize_google_chat_target(to)
        if not normalized:
            return {
                "ok": False,
                "error": missing_target_error("Google Chat", "<spaces/{space}|users/{user}>"),
            }
        return {"ok": True, "to": normalized}
    return {
        "ok": False,
        "error": missing_target_error("Google Chat", "<spaces/{space}|users/{user}>"),
    }


async def _send_text(params: dict) -> dict:
    account = resolve_google_chat_account(cfg=params["cfg"], account_id=params.get("accountId"))
    space = await resolve_google_chat_outbound_space({"account": account, "target": params["to"]})
    thread = (
        str(params["threadId"])
        if isinstance(params.get("threadId"), (int, float))
        else params.get("threadId") or params.get("replyToId")
    )
    runtime = load_google_chat_channel_runtime()
    result = await runtime["sendGoogleChatMessage"]({
        "account": account,
        "space": space,
        "text": params["text"],
        "thread": thread,
    })
    message_id = result.get("messageName", "") if result else ""
    return {
        "messageId": message_id,
        "chatId": space,
        "receipt": _create_google_chat_send_receipt({
            "messageId": message_id,
            "chatId": space,
            "kind": "text",
        }),
    }


async def _send_media(params: dict) -> dict:
    media_url = params.get("mediaUrl")
    if not media_url:
        raise RuntimeError("Google Chat mediaUrl is required.")
    account = resolve_google_chat_account(cfg=params["cfg"], account_id=params.get("accountId"))
    space = await resolve_google_chat_outbound_space({"account": account, "target": params["to"]})
    thread = (
        str(params["threadId"])
        if isinstance(params.get("threadId"), (int, float))
        else params.get("threadId") or params.get("replyToId")
    )
    max_bytes = resolve_channel_media_max_bytes({
        "cfg": params["cfg"],
        "resolveChannelLimitMb": lambda p: (
            ((p["cfg"].get("channels") or {}).get("googlechat") or {}).get("accounts", {}).get(p["accountId"], {}).get("mediaMaxMb")
            or ((p["cfg"].get("channels") or {}).get("googlechat") or {}).get("mediaMaxMb")
        ),
        "accountId": params.get("accountId"),
    })
    effective_max_bytes = max_bytes or (account.config.get("mediaMaxMb", 20) * 1024 * 1024)
    if media_url.startswith(("http://", "https://")):
        loaded = await read_remote_media_buffer({"url": media_url, "maxBytes": effective_max_bytes})
    else:
        loaded = await load_outbound_media_from_url(media_url, {
            "maxBytes": effective_max_bytes,
            "mediaAccess": params.get("mediaAccess"),
            "mediaLocalRoots": params.get("mediaLocalRoots"),
            "mediaReadFile": params.get("mediaReadFile"),
        })
    runtime = load_google_chat_channel_runtime()
    upload = await runtime["uploadGoogleChatAttachment"]({
        "account": account,
        "space": space,
        "filename": loaded.get("fileName", "attachment"),
        "buffer": loaded["buffer"],
        "contentType": loaded.get("contentType"),
    })
    attachments = None
    if upload.get("attachmentUploadToken"):
        attachments = [{
            "attachmentUploadToken": upload["attachmentUploadToken"],
            "contentName": loaded.get("fileName"),
        }]
    result = await runtime["sendGoogleChatMessage"]({
        "account": account,
        "space": space,
        "text": params.get("text"),
        "thread": thread,
        "attachments": attachments,
    })
    message_id = result.get("messageName", "") if result else ""
    return {
        "messageId": message_id,
        "chatId": space,
        "receipt": _create_google_chat_send_receipt({
            "messageId": message_id,
            "chatId": space,
            "kind": "media",
        }),
    }


googlechat_outbound_adapter = {
    "base": {
        "deliveryMode": "direct",
        "chunker": chunk_text_for_outbound,
        "chunkerMode": "markdown",
        "textChunkLimit": 4000,
        "sanitizeText": _sanitize_text,
        "normalizePayload": _normalize_payload,
        "resolveTarget": _resolve_target,
    },
    "attachedResults": {
        "channel": "googlechat",
        "sendText": _send_text,
        "sendMedia": _send_media,
    },
}

googlechat_message_adapter = define_channel_message_adapter({
    "id": "googlechat",
    "durableFinal": {
        "capabilities": {
            "text": True,
            "media": True,
            "thread": True,
            "messageSendingHooks": True,
        },
    },
    "send": {
        "text": _send_text,
        "media": _send_media,
    },
})

__all__ = [
    "PAIRING_APPROVED_MESSAGE",
    "googlechat_groups_adapter",
    "googlechat_directory_adapter",
    "googlechat_security_adapter",
    "googlechat_threading_adapter",
    "googlechat_pairing_text_adapter",
    "googlechat_outbound_adapter",
    "googlechat_message_adapter",
    "googlechat_message_adapter",
]