"""Resolves channel/account/thread run context for agent command execution."""

from __future__ import annotations

from openclaw.agents.command.types import AgentCommandOpts, AgentRunContext


def _normalize_account_id(value: str | None) -> str | None:
    trimmed = (value or "").strip()
    return trimmed if trimmed else None


def _resolve_message_channel(*candidates: str | None) -> str | None:
    for c in candidates:
        trimmed = (c or "").strip()
        if trimmed:
            return trimmed
    return None


def _stringify_route_thread_id(thread_id: str | int | None) -> str | None:
    if thread_id is None or thread_id == "":
        return None
    return str(thread_id).strip() or None


def resolve_agent_run_context(opts: AgentCommandOpts) -> AgentRunContext:
    merged: AgentRunContext = dict(opts.get("runContext") or {})

    normalized_channel = _resolve_message_channel(
        merged.get("messageChannel"),
        opts.get("messageChannel"),
        opts.get("replyChannel"),
        opts.get("channel"),
    )
    if normalized_channel:
        merged["messageChannel"] = normalized_channel

    account = _normalize_account_id(merged.get("accountId") or opts.get("accountId"))
    if account:
        merged["accountId"] = account

    for key, opt_key in (
        ("groupId", "groupId"),
        ("groupChannel", "groupChannel"),
        ("groupSpace", "groupSpace"),
    ):
        val = (merged.get(key) or opts.get(opt_key))
        if val is not None:
            s = str(val).strip()
            if s:
                merged[key] = s

    if merged.get("currentThreadTs") is None and opts.get("threadId") not in (None, ""):
        thread = _stringify_route_thread_id(opts.get("threadId"))
        if thread:
            merged["currentThreadTs"] = thread

    if not merged.get("currentChannelId") and opts.get("to"):
        trimmed = opts["to"].strip()
        if trimmed:
            merged["currentChannelId"] = trimmed

    return merged