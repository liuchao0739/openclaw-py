"""Diagnostic session state tracker for stuck-session detection.

Mirrors src/logging/diagnostic-session-state.ts.
"""

from __future__ import annotations

import time
from typing import Any

diagnostic_session_states: dict[str, dict[str, Any]] = {}

SESSION_STATE_TTL_MS = 30 * 60 * 1000
SESSION_STATE_PRUNE_INTERVAL_MS = 60 * 1000
SESSION_STATE_MAX_ENTRIES = 2000

_last_session_prune_at = 0


def _now_ms() -> int:
    return int(time.time() * 1000)


def prune_diagnostic_session_states(now: int | None = None, force: bool = False) -> None:
    global _last_session_prune_at
    current = now if now is not None else _now_ms()
    should_prune_for_size = len(diagnostic_session_states) > SESSION_STATE_MAX_ENTRIES
    if not force and not should_prune_for_size and current - _last_session_prune_at < SESSION_STATE_PRUNE_INTERVAL_MS:
        return
    _last_session_prune_at = current

    stale_keys = []
    for key, state in diagnostic_session_states.items():
        age_ms = current - state.get("lastActivity", 0)
        is_idle = state.get("state") == "idle"
        if is_idle and state.get("queueDepth", 0) <= 0 and age_ms > SESSION_STATE_TTL_MS:
            stale_keys.append(key)
    for key in stale_keys:
        del diagnostic_session_states[key]

    if len(diagnostic_session_states) <= SESSION_STATE_MAX_ENTRIES:
        return
    excess = len(diagnostic_session_states) - SESSION_STATE_MAX_ENTRIES
    ordered = sorted(
        diagnostic_session_states.items(),
        key=lambda item: item[1].get("lastActivity", 0),
    )
    for i in range(min(excess, len(ordered))):
        key = ordered[i][0]
        diagnostic_session_states.pop(key, None)


def _resolve_session_key(ref: dict[str, Any]) -> str:
    return ref.get("sessionKey") or ref.get("sessionId") or "unknown"


def _find_state_entry_by_session_id(session_id: str) -> tuple[str, dict[str, Any]] | None:
    for key, state in diagnostic_session_states.items():
        if state.get("sessionId") == session_id:
            return (key, state)
    return None


def _session_state_priority(state: str) -> int:
    priorities = {"idle": 0, "waiting": 1, "processing": 2}
    return priorities.get(state, 0)


def _merge_session_state(target: dict[str, Any], source: dict[str, Any]) -> None:
    source_is_newer = source.get("lastActivity", 0) > target.get("lastActivity", 0)
    source_is_same_age_and_more_active = (
        source.get("lastActivity", 0) == target.get("lastActivity", 0)
        and _session_state_priority(source.get("state", "idle"))
        > _session_state_priority(target.get("state", "idle"))
    )
    if target.get("sessionId") is None:
        target["sessionId"] = source.get("sessionId")
    if target.get("sessionKey") is None:
        target["sessionKey"] = source.get("sessionKey")
    if source.get("sessionFile") and (source_is_newer or not target.get("sessionFile")):
        target["sessionFile"] = source.get("sessionFile")
    if source_is_newer or source_is_same_age_and_more_active:
        target["state"] = source.get("state")
    target["generation"] = max(target.get("generation", 0), source.get("generation", 0))
    target["lastActivity"] = max(target.get("lastActivity", 0), source.get("lastActivity", 0))
    target["queueDepth"] = target.get("queueDepth", 0) + source.get("queueDepth", 0)
    target["activeQueuedTurn"] = target.get("activeQueuedTurn") or source.get("activeQueuedTurn")

    source_tool_history = source.get("toolCallHistory") or []
    if source_tool_history:
        target["toolCallHistory"] = (target.get("toolCallHistory") or []) + source_tool_history

    source_buckets = source.get("toolLoopWarningBuckets")
    if source_buckets:
        target_buckets = target.setdefault("toolLoopWarningBuckets", {})
        for bucket, count in source_buckets.items():
            target_buckets[bucket] = max(target_buckets.get(bucket, 0), count)

    source_poll_counts = source.get("commandPollCounts")
    if source_poll_counts:
        target_counts = target.setdefault("commandPollCounts", {})
        for command, value in source_poll_counts.items():
            existing = target_counts.get(command)
            if not existing or value.get("lastPollAt", 0) > existing.get("lastPollAt", 0):
                target_counts[command] = value


def get_diagnostic_session_state(ref: dict[str, Any]) -> dict[str, Any]:
    prune_diagnostic_session_states()
    key = _resolve_session_key(ref)
    direct = diagnostic_session_states.get(key)
    session_id_entry = _find_state_entry_by_session_id(ref["sessionId"]) if ref.get("sessionId") else None
    existing = direct or (session_id_entry[1] if session_id_entry else None)
    if existing:
        if direct and session_id_entry and session_id_entry[1] is not direct:
            _merge_session_state(direct, session_id_entry[1])
            diagnostic_session_states.pop(session_id_entry[0], None)
        elif not direct and ref.get("sessionKey") and session_id_entry:
            diagnostic_session_states.pop(session_id_entry[0], None)
            diagnostic_session_states[key] = existing
        if ref.get("sessionId"):
            existing["sessionId"] = ref["sessionId"]
        if ref.get("sessionKey"):
            existing["sessionKey"] = ref["sessionKey"]
        if ref.get("sessionFile"):
            existing["sessionFile"] = ref["sessionFile"]
        return existing
    created: dict[str, Any] = {
        "sessionId": ref.get("sessionId"),
        "sessionKey": ref.get("sessionKey"),
        "sessionFile": ref.get("sessionFile"),
        "lastActivity": _now_ms(),
        "generation": 0,
        "state": "idle",
        "queueDepth": 0,
    }
    diagnostic_session_states[key] = created
    prune_diagnostic_session_states(_now_ms(), True)
    return created


def peek_diagnostic_session_state(ref: dict[str, Any]) -> dict[str, Any] | None:
    key = _resolve_session_key(ref)
    direct = diagnostic_session_states.get(key)
    if direct:
        return direct
    if ref.get("sessionId"):
        entry = _find_state_entry_by_session_id(ref["sessionId"])
        if entry:
            return entry[1]
    return None


def get_diagnostic_session_state_count_for_test() -> int:
    return len(diagnostic_session_states)


def reset_diagnostic_session_state_for_test() -> None:
    global _last_session_prune_at
    diagnostic_session_states.clear()
    _last_session_prune_at = 0


def is_diagnostic_session_state_current(params: dict[str, Any]) -> bool:
    if params.get("generation") is None:
        return True
    state = peek_diagnostic_session_state(params)
    if not state:
        return False
    return (
        state.get("generation", 0) == params["generation"]
        and (params.get("state") is None or state.get("state") == params["state"])
    )


__all__ = [
    "diagnostic_session_states",
    "prune_diagnostic_session_states",
    "get_diagnostic_session_state",
    "peek_diagnostic_session_state",
    "get_diagnostic_session_state_count_for_test",
    "reset_diagnostic_session_state_for_test",
    "is_diagnostic_session_state_current",
]
