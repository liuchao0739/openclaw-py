from __future__ import annotations

from typing import Any


def resolve_google_chat_durable_reply_options(params: dict) -> dict | bool:
    info_kind = params.get("infoKind")
    if info_kind != "final" or params.get("typingMessageName"):
        return False
    payload = params.get("payload", {})
    thread_id = (payload.get("replyToId") or "").strip() or None
    result = {"to": params["spaceId"]}
    if thread_id:
        result["replyToId"] = thread_id
        result["threadId"] = thread_id
    return result


__all__ = ["resolve_google_chat_durable_reply_options"]