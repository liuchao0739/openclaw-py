"""Discord plugin module implements thread bindings.lifecycle behavior."""

from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw_extensions.discord.src.monitor.thread_bindings_state import (
    BINDINGS_BY_THREAD_ID,
    get_thread_binding_manager,
    normalize_thread_id,
    remove_binding_record,
    resolve_binding_ids_for_session,
)
from openclaw_extensions.discord.src.monitor.thread_bindings_types import (
    ThreadBindingRecord,
    ThreadBindingTargetKind,
)
from openclaw_extensions.discord.src.targets import parse_discord_target


def list_thread_bindings_by_session_key(
    *,
    target_session_key: str,
    account_id: str | None = None,
    target_kind: ThreadBindingTargetKind | None = None,
) -> list[ThreadBindingRecord]:
    ids = resolve_binding_ids_for_session(
        target_session_key=target_session_key,
        account_id=account_id,
        target_kind=target_kind,
    )
    return [
        record
        for binding_key in ids
        if (record := BINDINGS_BY_THREAD_ID.get(binding_key)) is not None
    ]


async def auto_bind_spawned_discord_subagent(params: dict[str, Any]) -> ThreadBindingRecord | None:
    channel = normalize_optional_lowercase_string(params.get("channel"))
    if channel != "discord":
        return None
    manager = get_thread_binding_manager(params.get("accountId"))
    if manager is None:
        return None
    bind_target = getattr(manager, "bind_target", None)
    if not callable(bind_target):
        return None

    requester_thread_id = normalize_thread_id(params.get("threadId"))
    channel_id = ""
    if requester_thread_id:
        existing = getattr(manager, "get_by_thread_id", lambda _id: None)(requester_thread_id)
        if existing and getattr(existing, "channel_id", "").strip():
            channel_id = existing.channel_id.strip()

    if not channel_id:
        to = normalize_optional_string(params.get("to")) or ""
        if not to:
            return None
        try:
            target = parse_discord_target(to, {"defaultKind": "channel"})
            if target is None or target.kind != "channel":
                return None
            channel_id = target.id
        except ValueError:
            return None

    agent_id = str(params.get("agentId") or "subagent").strip() or "subagent"
    return await bind_target(
        thread_id=None,
        channel_id=channel_id,
        create_thread=True,
        thread_name=f"{agent_id} session",
        target_kind="subagent",
        target_session_key=params["childSessionKey"],
        agent_id=agent_id,
        label=params.get("label"),
        bound_by=params.get("boundBy") or "system",
        intro_text=None,
    )


def unbind_thread_bindings_by_session_key(
    *,
    target_session_key: str,
    account_id: str | None = None,
    target_kind: ThreadBindingTargetKind | None = None,
    reason: str | None = None,
    send_farewell: bool | None = None,
    farewell_text: str | None = None,
) -> list[ThreadBindingRecord]:
    ids = resolve_binding_ids_for_session(
        target_session_key=target_session_key,
        account_id=account_id,
        target_kind=target_kind,
    )
    removed: list[ThreadBindingRecord] = []
    for binding_key in ids:
        record = BINDINGS_BY_THREAD_ID.get(binding_key)
        if record is None:
            continue
        remove_binding_record(record)
        removed.append(record)
    return removed


__all__ = [
    "auto_bind_spawned_discord_subagent",
    "list_thread_bindings_by_session_key",
    "unbind_thread_bindings_by_session_key",
]
