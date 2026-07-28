from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.channel_actions import (
    create_action_gate,
    json_result,
    read_reaction_params,
    read_string_param,
)
from openclaw.plugin_sdk.tool_send import extract_tool_send
from openclaw_extensions.googlechat.src.accounts import (
    ResolvedGoogleChatAccount,
    list_google_chat_account_ids,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.api import (
    create_google_chat_reaction,
    delete_google_chat_reaction,
    list_google_chat_reactions,
    send_google_chat_message,
    upload_google_chat_attachment,
)
from openclaw_extensions.googlechat.src.runtime import get_google_chat_runtime
from openclaw_extensions.googlechat.src.targets import resolve_google_chat_outbound_space

provider_id = "googlechat"


def _list_enabled_accounts(cfg: dict) -> list[ResolvedGoogleChatAccount]:
    return [
        a for a in [resolve_google_chat_account(cfg=cfg, account_id=aid) for aid in list_google_chat_account_ids(cfg)]
        if a.enabled and a.credential_source != "none"
    ]


def _is_reactions_enabled(accounts: list) -> bool:
    for account in accounts:
        gate = create_action_gate(account.config.get("actions", {}))
        if gate("reactions"):
            return True
    return False


def _resolve_app_user_names(account: dict) -> set[str]:
    return {"users/app", account.config.get("botUser", "").strip()}.difference({""})


async def _load_google_chat_action_media(params: dict) -> dict:
    runtime = get_google_chat_runtime()
    media_url = params["mediaUrl"]
    max_bytes = params["maxBytes"]
    if media_url.startswith(("http://", "https://")):
        return await runtime.channel.media.read_remote_media_buffer({
            "url": media_url,
            "maxBytes": max_bytes,
        })
    from openclaw.plugin_sdk.outbound_media import load_outbound_media_from_url
    return await load_outbound_media_from_url(media_url, {
        "maxBytes": max_bytes,
        "mediaAccess": params.get("mediaAccess"),
        "mediaLocalRoots": params.get("mediaLocalRoots"),
        "mediaReadFile": params.get("mediaReadFile"),
    })


async def _describe_message_tool(params: dict) -> dict | None:
    cfg = params.get("cfg")
    account_id = params.get("accountId")
    if account_id:
        accounts = [resolve_google_chat_account(cfg=cfg, account_id=account_id)]
        accounts = [a for a in accounts if a.enabled and a.credential_source != "none"]
    else:
        accounts = _list_enabled_accounts(cfg)
    if len(accounts) == 0:
        return None
    actions = {"send", "upload-file"}
    if _is_reactions_enabled(accounts):
        actions.add("react")
        actions.add("reactions")
    return {"actions": list(actions)}


async def _handle_action(params: dict) -> Any:
    action = params.get("action")
    action_params = params.get("params", {})
    cfg = params.get("cfg")
    account_id = params.get("accountId")
    media_access = params.get("mediaAccess")
    media_local_roots = params.get("mediaLocalRoots")
    media_read_file = params.get("mediaReadFile")

    account = resolve_google_chat_account(cfg=cfg, account_id=account_id)
    if account.credential_source == "none":
        raise RuntimeError("Google Chat credentials are missing.")

    if action in ("send", "upload-file"):
        to = read_string_param(action_params, "to", required=True)
        content = (
            read_string_param(action_params, "message", required=(action == "send"), allow_empty=True)
            or read_string_param(action_params, "initialComment", allow_empty=True)
            or ""
        )
        media_url = (
            read_string_param(action_params, "media", trim=False)
            or read_string_param(action_params, "filePath", trim=False)
            or read_string_param(action_params, "path", trim=False)
        )
        thread_id = read_string_param(action_params, "threadId") or read_string_param(action_params, "replyTo")
        space = await resolve_google_chat_outbound_space({"account": account, "target": to})

        if media_url:
            max_bytes = (account.config.get("mediaMaxMb", 20)) * 1024 * 1024
            loaded = await _load_google_chat_action_media({
                "mediaUrl": media_url,
                "maxBytes": max_bytes,
                "mediaAccess": media_access,
                "mediaLocalRoots": media_local_roots,
                "mediaReadFile": media_read_file,
            })
            upload_file_name = (
                read_string_param(action_params, "filename")
                or read_string_param(action_params, "title")
                or loaded.get("fileName", "")
                or "attachment"
            )
            upload = await upload_google_chat_attachment({
                "account": account,
                "space": space,
                "filename": upload_file_name,
                "buffer": loaded["buffer"],
                "contentType": loaded.get("contentType"),
            })
            sent = await send_google_chat_message({
                "account": account,
                "space": space,
                "text": content,
                "thread": thread_id,
                "attachments": (
                    [{"attachmentUploadToken": upload["attachmentUploadToken"], "contentName": upload_file_name}]
                    if upload.get("attachmentUploadToken")
                    else None
                ),
            })
            return json_result({"ok": True, "to": space, **(sent or {})})

        if action == "upload-file":
            raise RuntimeError("upload-file requires media, filePath, or path")

        sent = await send_google_chat_message({
            "account": account,
            "space": space,
            "text": content,
            "thread": thread_id,
        })
        return json_result({"ok": True, "to": space, **(sent or {})})

    if action == "react":
        message_name = read_string_param(action_params, "messageId", required=True)
        emoji, remove, is_empty = read_reaction_params(action_params)
        if remove or is_empty:
            reactions = await list_google_chat_reactions({"account": account, "messageName": message_name})
            app_users = _resolve_app_user_names(account)
            to_remove = []
            for reaction in reactions:
                user_name = (reaction.get("user") or {}).get("name", "").strip()
                if app_users and user_name not in app_users:
                    continue
                if emoji and (reaction.get("emoji") or {}).get("unicode") != emoji:
                    continue
                to_remove.append(reaction)
            for reaction in to_remove:
                if not reaction.get("name"):
                    continue
                await delete_google_chat_reaction({"account": account, "reactionName": reaction["name"]})
            return json_result({"ok": True, "removed": len(to_remove)})

        reaction = await create_google_chat_reaction({
            "account": account,
            "messageName": message_name,
            "emoji": emoji,
        })
        return json_result({"ok": True, "reaction": reaction})

    if action == "reactions":
        message_name = read_string_param(action_params, "messageId", required=True)
        limit = action_params.get("limit")
        reactions = await list_google_chat_reactions({
            "account": account,
            "messageName": message_name,
            "limit": limit,
        })
        return json_result({"ok": True, "reactions": reactions})

    raise RuntimeError(f"Action {action} is not supported for provider {provider_id}.")


googlechat_message_actions = {
    "describeMessageTool": _describe_message_tool,
    "extractToolSend": lambda params: extract_tool_send(params.get("args"), "sendMessage"),
    "handleAction": _handle_action,
}

__all__ = ["googlechat_message_actions"]