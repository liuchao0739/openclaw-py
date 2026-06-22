"""Run timeout behavior while compaction is in progress."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

ContinuableRole = Literal[
    "user",
    "toolResult",
    "branchSummary",
    "compactionSummary",
    "custom",
    "bashExecution",
]


def should_flag_compaction_timeout(
    *,
    is_timeout: bool,
    is_compaction_pending_or_retrying: bool,
    is_compaction_in_flight: bool,
) -> bool:
    if not is_timeout:
        return False
    return is_compaction_pending_or_retrying or is_compaction_in_flight


def resolve_run_timeout_during_compaction(
    *,
    is_compaction_pending_or_retrying: bool,
    is_compaction_in_flight: bool,
    grace_already_used: bool,
) -> Literal["extend", "abort"]:
    if not is_compaction_pending_or_retrying and not is_compaction_in_flight:
        return "abort"
    return "abort" if grace_already_used else "extend"


def _can_continue_from_message(message: dict[str, Any] | None) -> bool:
    if not message or not isinstance(message, dict):
        return False
    role = message.get("role")
    if role in ("user", "toolResult", "branchSummary", "compactionSummary", "custom"):
        return True
    if role == "bashExecution":
        return message.get("excludeFromContext") is not True
    return False


def _trim_to_continuable_tail(messages: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    end = len(messages)
    while end > 0 and not _can_continue_from_message(messages[end - 1]):
        end -= 1
    return messages[:end] if end > 0 else None


class SnapshotSelection(TypedDict):
    messagesSnapshot: list[dict[str, Any]]
    sessionIdUsed: str
    source: Literal["pre-compaction", "current"]


def select_compaction_timeout_snapshot(
    *,
    timed_out_during_compaction: bool,
    pre_compaction_snapshot: list[dict[str, Any]] | None,
    pre_compaction_session_id: str,
    current_snapshot: list[dict[str, Any]],
    current_session_id: str,
) -> SnapshotSelection:
    if not timed_out_during_compaction:
        return {
            "messagesSnapshot": current_snapshot,
            "sessionIdUsed": current_session_id,
            "source": "current",
        }

    if pre_compaction_snapshot:
        continuable = _trim_to_continuable_tail(pre_compaction_snapshot)
        if continuable:
            return {
                "messagesSnapshot": continuable,
                "sessionIdUsed": pre_compaction_session_id,
                "source": "pre-compaction",
            }

    continuable_current = _trim_to_continuable_tail(current_snapshot)
    if continuable_current:
        return {
            "messagesSnapshot": continuable_current,
            "sessionIdUsed": current_session_id,
            "source": "current",
        }

    return {
        "messagesSnapshot": [],
        "sessionIdUsed": current_session_id,
        "source": "current",
    }