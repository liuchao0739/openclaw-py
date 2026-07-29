"""Diagnostic run activity helpers summarize run lifecycle activity for diagnostics.

Mirrors src/logging/diagnostic-run-activity.ts.
"""

from __future__ import annotations

import time
from typing import Any

_session_activities: dict[str, dict[str, Any]] = {}


def _resolve_session_key(ref: dict[str, Any]) -> str:
    return ref.get("sessionKey") or ref.get("sessionId") or "unknown"


def get_diagnostic_session_activity_snapshot(ref: dict[str, Any]) -> dict[str, Any]:
    key = _resolve_session_key(ref)
    activity = _session_activities.get(key)
    if not activity:
        return {
            "activeWorkKind": None,
            "hasActiveEmbeddedRun": False,
            "lastProgressAgeMs": None,
            "activeToolAgeMs": None,
        }
    now = int(time.time() * 1000)
    last_progress_at = activity.get("lastProgressAt", 0)
    return {
        "activeWorkKind": activity.get("activeWorkKind"),
        "hasActiveEmbeddedRun": len(activity.get("activeEmbeddedRuns", {})) > 0,
        "lastProgressAgeMs": (now - last_progress_at) if last_progress_at else None,
        "activeToolAgeMs": None,
    }


def reset_diagnostic_run_activity_for_test() -> None:
    _session_activities.clear()


__all__ = [
    "get_diagnostic_session_activity_snapshot",
    "reset_diagnostic_run_activity_for_test",
]
