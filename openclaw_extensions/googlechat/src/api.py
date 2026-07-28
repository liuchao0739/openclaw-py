from __future__ import annotations

import json
import uuid
from typing import Any

import aiohttp

from openclaw.plugin_sdk.error_runtime import format_error_message
from openclaw.plugin_sdk.media_runtime import parse_media_content_length
from openclaw.plugin_sdk.response_limit_runtime import read_response_with_limit
from openclaw.plugin_sdk.ssrf_runtime import fetch_with_ssr_fguard
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.approval_card_actions import (
    should_suppress_google_chat_manual_exec_approval_followup_text,
)
from openclaw_extensions.googlechat.src.auth import get_google_chat_access_token
from openclaw_extensions.googlechat.src.types import GoogleChatCardV2, GoogleChatReaction

CHAT_API_BASE = "https://chat.googleapis.com/v1"
CHAT_UPLOAD_BASE = "https://chat.googleapis.com/upload/v1"


async def _read_google_chat_json_response(response: aiohttp.ClientResponse, label: str) -> Any:
    try:
        return await response.json()
    except Exception as cause:
        raise RuntimeError(f"{label}: malformed JSON response") from cause


def _headers_to_dict(headers: aiohttp.Multidict | None = None) -> dict[str, str]:
    if headers is None:
        return {}
    return dict(headers)


async def _with_google_chat_response(params: dict) -> Any:
    account = params["account"]
    url = params["url"]
    init = params.get("init", {})
    audit_context = params["auditContext"]
    error_prefix = params.get("errorPrefix", "Google Chat API")
    handle_response = params["handleResponse"]

    token = await get_google_chat_access_token(account)
    headers = _headers_to_dict(init.get("headers"))
    headers["Authorization"] = f"Bearer {token}"
    init["headers"] = headers

    result = await fetch_with_ssr_fguard({
        "url": url,
        "init": init,
        "auditContext": audit_context,
    })
    response = result.get("response")
    release = result.get("release", lambda: None)

    try:
        if not response or not response.ok:
            text = ""
            if response:
                try:
                    text = await response.text()
                except Exception:
                    pass
            status = response.status if response else 0
            raise RuntimeError(f"{error_prefix} {status}: {text or 'Unknown error'}")
        return await handle_response(response)
    finally:
        if callable(release):
            await release()


async def _fetch_json(account: ResolvedGoogleChatAccount, url: str, init: dict) -> Any:
    headers = _headers_to_dict(init.get("headers"))
    headers["Content-Type"] = "application/json"
    init["headers"] = headers
    return await _with_google_chat_response({
        "account": account,
        "url": url,
        "init": init,
        "auditContext": "googlechat.api.json",
        "handleResponse": lambda response: _read_google_chat_json_response(
            response, "Google Chat API request failed"
        ),
    })


async def _fetch_ok(account: ResolvedGoogleChatAccount, url: str, init: dict) -> None:
    await _with_google_chat_response({
        "account": account,
        "url": url,
        "init": init,
        "auditContext": "googlechat.api.ok",
        "handleResponse": lambda response: None,
    })


async def _fetch_buffer(
    account: ResolvedGoogleChatAccount,
    url: str,
    init: dict | None = None,
    options: dict | None = None,
) -> dict:
    if init is None:
        init = {}
    if options is None:
        options = {}

    max_bytes = options.get("maxBytes")

    async def handle_response(response: aiohttp.ClientResponse) -> dict:
        length_header = response.headers.get("content-length")
        if max_bytes and length_header:
            length = parse_media_content_length(length_header)
            if length is not None and length > max_bytes:
                raise RuntimeError(f"Google Chat media exceeds max bytes ({max_bytes})")
        if not max_bytes:
            data = await response.read()
            content_type = response.headers.get("content-type")
            return {"buffer": data, "contentType": content_type}
        data = await read_response_with_limit(response, max_bytes)
        content_type = response.headers.get("content-type")
        return {"buffer": data, "contentType": content_type}

    return await _with_google_chat_response({
        "account": account,
        "url": url,
        "init": init,
        "auditContext": "googlechat.api.buffer",
        "handleResponse": handle_response,
    })


async def send_google_chat_message(params: dict) -> dict | None:
    account = params["account"]
    space = params["space"]
    text = params.get("text")
    thread = params.get("thread")
    cards_v2 = params.get("cardsV2")
    attachments = params.get("attachments")

    if (
        text
        and (not cards_v2 or len(cards_v2) == 0)
        and (not attachments or len(attachments) == 0)
        and should_suppress_google_chat_manual_exec_approval_followup_text(text)
    ):
        return None

    body: dict[str, Any] = {}
    if text:
        body["text"] = text
    if cards_v2 and len(cards_v2) > 0:
        body["cardsV2"] = cards_v2
    if thread:
        body["thread"] = {"name": thread}
    if attachments and len(attachments) > 0:
        body["attachment"] = [
            {
                "attachmentDataRef": {"attachmentUploadToken": item["attachmentUploadToken"]},
                **({"contentName": item["contentName"]} if item.get("contentName") else {}),
            }
            for item in attachments
        ]

    url = f"{CHAT_API_BASE}/{space}/messages"
    if thread:
        url += "?messageReplyOption=REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"

    result = await _fetch_json(account, url, {
        "method": "POST",
        "body": json.dumps(body),
    })
    if result:
        return {
            "messageName": result.get("name"),
            "threadName": (result.get("thread") or {}).get("name"),
        }
    return None


async def update_google_chat_message(params: dict) -> dict:
    account = params["account"]
    message_name = params["messageName"]
    text = params.get("text")
    cards_v2 = params.get("cardsV2")

    update_mask = []
    if text is not None:
        update_mask.append("text")
    if cards_v2 is not None:
        update_mask.append("cardsV2")
    if len(update_mask) == 0:
        raise RuntimeError("Google Chat message update requires text or cardsV2.")

    url = f"{CHAT_API_BASE}/{message_name}?updateMask={','.join(update_mask)}"
    body: dict[str, Any] = {}
    if text is not None:
        body["text"] = text
    if cards_v2 is not None:
        body["cardsV2"] = cards_v2

    result = await _fetch_json(account, url, {
        "method": "PATCH",
        "body": json.dumps(body),
    })
    return {"messageName": result.get("name")}


async def delete_google_chat_message(params: dict) -> None:
    account = params["account"]
    message_name = params["messageName"]
    url = f"{CHAT_API_BASE}/{message_name}"
    await _fetch_ok(account, url, {"method": "DELETE"})


async def upload_google_chat_attachment(params: dict) -> dict:
    account = params["account"]
    space = params["space"]
    filename = params["filename"]
    buffer_data = params["buffer"]
    content_type = params.get("contentType")

    boundary = f"openclaw-{uuid.uuid4()}"
    metadata = json.dumps({"filename": filename})
    header = f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadata}\r\n"
    media_header = f"--{boundary}\r\nContent-Type: {content_type or 'application/octet-stream'}\r\n\r\n"
    footer = f"\r\n--{boundary}--\r\n"
    body = header.encode("utf-8") + media_header.encode("utf-8") + buffer_data + footer.encode("utf-8")

    url = f"{CHAT_UPLOAD_BASE}/{space}/attachments:upload?uploadType=multipart"
    payload = await _with_google_chat_response({
        "account": account,
        "url": url,
        "init": {
            "method": "POST",
            "headers": {"Content-Type": f"multipart/related; boundary={boundary}"},
            "body": body,
        },
        "auditContext": "googlechat.upload",
        "errorPrefix": "Google Chat upload",
        "handleResponse": lambda response: _read_google_chat_json_response(
            response, "Google Chat upload failed"
        ),
    })
    return {
        "attachmentUploadToken": (payload.get("attachmentDataRef") or {}).get("attachmentUploadToken"),
    }


async def download_google_chat_media(params: dict) -> dict:
    account = params["account"]
    resource_name = params["resourceName"]
    max_bytes = params.get("maxBytes")
    url = f"{CHAT_API_BASE}/media/{resource_name}?alt=media"
    return await _fetch_buffer(account, url, None, {"maxBytes": max_bytes})


async def create_google_chat_reaction(params: dict) -> GoogleChatReaction:
    account = params["account"]
    message_name = params["messageName"]
    emoji = params["emoji"]
    url = f"{CHAT_API_BASE}/{message_name}/reactions"
    return await _fetch_json(account, url, {
        "method": "POST",
        "body": json.dumps({"emoji": {"unicode": emoji}}),
    })


async def list_google_chat_reactions(params: dict) -> list[GoogleChatReaction]:
    account = params["account"]
    message_name = params["messageName"]
    limit = params.get("limit")
    url = f"{CHAT_API_BASE}/{message_name}/reactions"
    if limit and limit > 0:
        url += f"?pageSize={limit}"
    result = await _fetch_json(account, url, {"method": "GET"})
    return result.get("reactions", [])


async def delete_google_chat_reaction(params: dict) -> None:
    account = params["account"]
    reaction_name = params["reactionName"]
    url = f"{CHAT_API_BASE}/{reaction_name}"
    await _fetch_ok(account, url, {"method": "DELETE"})


async def find_google_chat_direct_message(params: dict) -> dict | None:
    account = params["account"]
    user_name = params["userName"]
    url = f"{CHAT_API_BASE}/spaces:findDirectMessage?name={user_name}"
    return await _fetch_json(account, url, {"method": "GET"})


async def probe_google_chat(account: ResolvedGoogleChatAccount) -> dict:
    try:
        url = f"{CHAT_API_BASE}/spaces?pageSize=1"
        await _fetch_json(account, url, {"method": "GET"})
        return {"ok": True}
    except Exception as err:
        return {"ok": False, "error": format_error_message(err)}


__all__ = [
    "send_google_chat_message",
    "update_google_chat_message",
    "delete_google_chat_message",
    "upload_google_chat_attachment",
    "download_google_chat_media",
    "create_google_chat_reaction",
    "list_google_chat_reactions",
    "delete_google_chat_reaction",
    "find_google_chat_direct_message",
    "probe_google_chat",
]