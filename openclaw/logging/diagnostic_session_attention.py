"""Diagnostic session attention helpers summarize active work for session diagnostics.

Mirrors src/logging/diagnostic-session-attention.ts.
"""

from __future__ import annotations

from typing import Any, Literal


def classify_session_attention(params: dict[str, Any]) -> dict[str, Any]:
    activity = params.get("activity", {})
    stale_ms = params.get("staleMs", 0)
    if activity.get("activeWorkKind"):
        last_progress_age_ms = activity.get("lastProgressAgeMs") or 0
        if (
            params.get("state") == "idle"
            and params.get("queueDepth", 0) > 0
            and activity.get("hasActiveEmbeddedRun") is not True
            and last_progress_age_ms > stale_ms
        ):
            return {
                "eventType": "session.stuck",
                "reason": "queued_work_without_active_run",
                "classification": "stale_session_state",
                "recoveryEligible": True,
            }
        if (
            activity.get("activeWorkKind") == "tool_call"
            and (activity.get("activeToolAgeMs") or 0) > stale_ms
            and last_progress_age_ms > stale_ms
        ):
            return {
                "eventType": "session.stalled",
                "reason": "blocked_tool_call",
                "classification": "blocked_tool_call",
                "recoveryEligible": False,
            }
        if last_progress_age_ms > stale_ms:
            return {
                "eventType": "session.long_running",
                "reason": "active_work_stale",
                "classification": "long_running",
                "activeWorkKind": activity.get("activeWorkKind"),
                "recoveryEligible": False,
            }
    if params.get("queueDepth", 0) > 0 and params.get("state") != "processing":
        return {
            "eventType": "session.stuck",
            "reason": "queued_work_no_activity",
            "classification": "stale_session_state",
            "recoveryEligible": True,
        }
    return {
        "eventType": "session.long_running",
        "reason": "no_active_work",
        "classification": "long_running",
        "recoveryEligible": False,
    }


def is_terminal_diagnostic_progress_reason(reason: str | None) -> bool:
    if not reason:
        return False
    terminal_reasons = {"completed", "error", "aborted", "cancelled", "finished"}
    return reason in terminal_reasons


__all__ = ["classify_session_attention", "is_terminal_diagnostic_progress_reason"]
