"""Diagnostic session recovery types and helpers.

Mirrors src/logging/diagnostic-session-recovery.ts.
"""

from __future__ import annotations

from typing import Any


def resolve_stuck_session_recovery_ref(params: dict[str, Any]) -> str | None:
    session_key = params.get("sessionKey")
    if isinstance(session_key, str):
        session_key = session_key.strip()
        if session_key:
            return session_key
    session_id = params.get("sessionId")
    if isinstance(session_id, str):
        session_id = session_id.strip()
        if session_id:
            return session_id
    return None


def recovery_outcome_mutates_session_state(outcome: dict[str, Any] | None) -> bool:
    if not outcome:
        return False
    status = outcome.get("status")
    return (
        status == "aborted"
        or status == "released"
        or (status == "noop" and outcome.get("reason") == "no_active_work")
    )


def recovery_outcome_clears_queued_session_state(outcome: dict[str, Any]) -> bool:
    status = outcome.get("status")
    if status == "released":
        return True
    if status == "aborted" and outcome.get("released", 0) > 0 and (outcome.get("queuedCount") or 0) == 0:
        return True
    if status == "noop" and outcome.get("reason") == "no_active_work":
        return True
    return False


def recovery_outcome_released_count(outcome: dict[str, Any]) -> int:
    return outcome.get("released", 0) if "released" in outcome else 0


def format_recovery_outcome(outcome: dict[str, Any]) -> str:
    fields = [
        f"status={outcome.get('status')}",
        f"action={outcome.get('action')}",
        f"sessionId={outcome.get('sessionId') or outcome.get('activeSessionId') or 'unknown'}",
        f"sessionKey={outcome.get('sessionKey') or 'unknown'}",
    ]
    if outcome.get("activeSessionId"):
        fields.append(f"activeSessionId={outcome['activeSessionId']}")
    if outcome.get("activeWorkKind"):
        fields.append(f"activeWorkKind={outcome['activeWorkKind']}")
    if outcome.get("lane"):
        fields.append(f"lane={outcome['lane']}")
    if "reason" in outcome:
        fields.append(f"reason={outcome['reason']}")
    if "aborted" in outcome:
        fields.append(f"aborted={outcome['aborted']}")
        fields.append(f"drained={outcome['drained']}")
        fields.append(f"forceCleared={outcome['forceCleared']}")
    if "released" in outcome:
        fields.append(f"released={outcome['released']}")
    if outcome.get("status") == "aborted" and outcome.get("queuedCount") is not None:
        fields.append(f"queuedCount={outcome['queuedCount']}")
    if outcome.get("activeCount") is not None:
        fields.append(f"laneActive={outcome['activeCount']}")
    if outcome.get("status") == "skipped" and outcome.get("queuedCount") is not None:
        fields.append(f"laneQueued={outcome['queuedCount']}")
    if "error" in outcome:
        fields.append(f"error={outcome['error']}")
    return " ".join(fields)


__all__ = [
    "resolve_stuck_session_recovery_ref",
    "recovery_outcome_mutates_session_state",
    "recovery_outcome_clears_queued_session_state",
    "recovery_outcome_released_count",
    "format_recovery_outcome",
]
