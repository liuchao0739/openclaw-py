from __future__ import annotations

from openclaw.plugin_sdk.approval_gateway_runtime import resolve_approval_over_gateway
from openclaw_extensions.googlechat.src.approval_auth import google_chat_approval_auth
from openclaw_extensions.googlechat.src.approval_card_actions import (
    claim_google_chat_approval_card_binding,
    complete_google_chat_approval_card_binding,
    get_google_chat_approval_card_binding,
    release_google_chat_approval_card_binding,
    read_google_chat_approval_action_token,
)


def _log_ignored(target: dict, message: str) -> None:
    target["runtime"].get("log", lambda m: None)(
        f"[{target['account'].account_id}] googlechat approval ignored: {message}"
    )


async def maybe_handle_google_chat_approval_card_click(params: dict) -> bool:
    event = params["event"]
    target = params["target"]
    event_type = event.get("type") or event.get("eventType")
    if event_type != "CARD_CLICKED":
        return False

    token = read_google_chat_approval_action_token(event)
    if not token:
        return False

    binding = get_google_chat_approval_card_binding(token)
    if not binding:
        _log_ignored(target, "unknown or expired card token")
        return True
    if binding["accountId"] != target["account"].account_id:
        _log_ignored(target, "card token account mismatch")
        return True
    if event.get("space", {}).get("name") != binding["spaceName"]:
        _log_ignored(target, "card token space mismatch")
        return True
    if event.get("message", {}).get("name") and event["message"]["name"] != binding["messageName"]:
        _log_ignored(target, "card token message mismatch")
        return True
    if binding["decision"] not in binding.get("allowedDecisions", []):
        _log_ignored(target, "card token decision is no longer allowed")
        return True

    actor = (event.get("user") or {}).get("name")
    auth_result = google_chat_approval_auth.authorize_actor_action({
        "cfg": target["config"],
        "accountId": target["account"].account_id,
        "senderId": actor,
        "action": "approve",
        "approvalKind": binding["approvalKind"],
    })
    if not auth_result.get("authorized"):
        _log_ignored(target, f"unauthorized actor {actor or 'unknown'}")
        return True

    claim = claim_google_chat_approval_card_binding(token)
    if claim["kind"] == "missing":
        _log_ignored(target, "card token already consumed")
        return True
    if claim["kind"] == "in-flight":
        _log_ignored(target, "card token resolve already in flight")
        return True
    consumed = claim["binding"]

    try:
        await resolve_approval_over_gateway({
            "cfg": target["config"],
            "approvalId": consumed["approvalId"],
            "decision": consumed["decision"],
            "senderId": actor,
            "allowPluginFallback": consumed["approvalKind"] == "exec",
            "clientDisplayName": f"Google Chat approval ({(actor or 'unknown').strip()})",
        })
    except Exception as error:
        release_google_chat_approval_card_binding(token)
        raise error

    complete_google_chat_approval_card_binding(token)
    target["runtime"].get("log", lambda m: None)(
        f"[{target['account'].account_id}] googlechat approval resolved id={consumed['approvalId']} "
        f"decision={consumed['decision']} sender={actor or 'unknown'}"
    )
    return True


__all__ = ["maybe_handle_google_chat_approval_card_click"]