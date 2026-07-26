"""Discord plugin module implements subagent hooks behavior."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_stringified_id,
)
from openclaw_extensions.discord.src.accounts import resolve_discord_account
from openclaw_extensions.discord.src.monitor.thread_bindings import (
    ThreadBindingTargetKind,
    auto_bind_spawned_discord_subagent,
    list_thread_bindings_by_session_key,
    unbind_thread_bindings_by_session_key,
)
from openclaw_extensions.discord.src.thread_bindings_policy import (
    format_thread_binding_disabled_error,
    format_thread_binding_spawn_disabled_error,
    resolve_thread_binding_spawn_policy,
)


def _summarize_error(err: object) -> str:
    if isinstance(err, BaseException):
        return str(err)
    if isinstance(err, str):
        return err
    return "error"


def _normalize_thread_binding_target_kind(raw: str | None) -> ThreadBindingTargetKind | None:
    normalized = normalize_optional_lowercase_string(raw)
    if normalized in ("subagent", "acp"):
        return normalized
    return None


async def handle_discord_subagent_spawning(
    api: Any,
    event: dict[str, Any],
) -> dict[str, Any] | None:
    if not event.get("threadRequested"):
        return None
    channel = normalize_optional_lowercase_string((event.get("requester") or {}).get("channel"))
    if channel != "discord":
        return None
    account = resolve_discord_account(
        cfg=api.config,
        account_id=(event.get("requester") or {}).get("accountId"),
    )
    thread_binding_policy = resolve_thread_binding_spawn_policy(
        cfg=api.config,
        channel="discord",
        account_id=account.account_id,
        kind="subagent",
    )
    if not thread_binding_policy["enabled"]:
        return {
            "status": "error",
            "error": format_thread_binding_disabled_error(
                channel=thread_binding_policy["channel"],
                account_id=thread_binding_policy["accountId"],
                kind="subagent",
            ),
        }
    if not thread_binding_policy["spawnEnabled"]:
        return {
            "status": "error",
            "error": format_thread_binding_spawn_disabled_error(
                channel=thread_binding_policy["channel"],
                account_id=thread_binding_policy["accountId"],
                kind="subagent",
            ),
        }
    try:
        agent_id = str(event.get("agentId") or "subagent").strip() or "subagent"
        binding = await auto_bind_spawned_discord_subagent(
            {
                "cfg": api.config,
                "accountId": account.account_id,
                "channel": (event.get("requester") or {}).get("channel"),
                "to": (event.get("requester") or {}).get("to"),
                "threadId": (event.get("requester") or {}).get("threadId"),
                "childSessionKey": event["childSessionKey"],
                "agentId": agent_id,
                "label": event.get("label"),
                "boundBy": "system",
            }
        )
        if binding is None:
            return {
                "status": "error",
                "error": (
                    "Unable to create or bind a Discord thread for this subagent session. "
                    "Session mode is unavailable for this target."
                ),
            }
        return {
            "status": "ok",
            "threadBindingReady": True,
            "deliveryOrigin": {
                "channel": "discord",
                "accountId": account.account_id,
                "to": f"channel:{binding.thread_id}",
                "threadId": binding.thread_id,
            },
        }
    except Exception as err:  # noqa: BLE001
        return {
            "status": "error",
            "error": f"Discord thread bind failed: {_summarize_error(err)}",
        }


def handle_discord_subagent_ended(event: dict[str, Any]) -> None:
    unbind_thread_bindings_by_session_key(
        target_session_key=event["targetSessionKey"],
        account_id=event.get("accountId"),
        target_kind=_normalize_thread_binding_target_kind(event.get("targetKind")),
        reason=event.get("reason"),
        send_farewell=event.get("sendFarewell"),
    )


def handle_discord_subagent_delivery_target(event: dict[str, Any]) -> dict[str, Any] | None:
    if not event.get("expectsCompletionMessage"):
        return None
    requester_channel = normalize_optional_lowercase_string(
        (event.get("requesterOrigin") or {}).get("channel")
    )
    if requester_channel != "discord":
        return None
    requester_account_id = str((event.get("requesterOrigin") or {}).get("accountId") or "").strip()
    requester_origin = event.get("requesterOrigin") or {}
    requester_thread_id = (
        normalize_optional_stringified_id(requester_origin.get("threadId")) or ""
        if requester_origin.get("threadId") not in (None, "")
        else ""
    )
    bindings = list_thread_bindings_by_session_key(
        target_session_key=event["childSessionKey"],
        account_id=requester_account_id or None,
        target_kind="subagent",
    )
    if not bindings:
        return None

    binding = None
    if requester_thread_id:
        for entry in bindings:
            if entry.thread_id != requester_thread_id:
                continue
            if requester_account_id and entry.account_id != requester_account_id:
                continue
            binding = entry
            break
    if binding is None and len(bindings) == 1:
        binding = bindings[0]
    if binding is None:
        return None
    return {
        "origin": {
            "channel": "discord",
            "accountId": binding.account_id,
            "to": f"channel:{binding.thread_id}",
            "threadId": binding.thread_id,
        }
    }


__all__ = [
    "handle_discord_subagent_delivery_target",
    "handle_discord_subagent_ended",
    "handle_discord_subagent_spawning",
]
