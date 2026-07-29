"""Message lifecycle logging helpers emit queue and processing diagnostic events.

Mirrors src/logging/message-lifecycle.ts.
"""

from __future__ import annotations

import time
from typing import Any, Literal


def create_diagnostic_message_lifecycle(params: dict[str, Any]) -> dict[str, Any]:
    started_at_ms = params.get("startedAtMs") or int(time.time() * 1000)

    def resolve_ref(override: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "sessionId": (override or {}).get("sessionId") or params.get("sessionId"),
            "sessionKey": (override or {}).get("sessionKey") or params.get("sessionKey"),
        }

    def has_session_ref(ref: dict[str, Any]) -> bool:
        return bool(ref.get("sessionId") or ref.get("sessionKey"))

    def can_track_session_state(ref: dict[str, Any]) -> bool:
        return bool(params.get("enabled") and params.get("trackSessionState") and has_session_ref(ref))

    def mark_processing(override: dict[str, Any] | None = None) -> None:
        ref = resolve_ref(override)
        if not can_track_session_state(ref):
            return

    def mark_idle(reason: str | None = None, override: dict[str, Any] | None = None) -> None:
        ref = resolve_ref(override)
        if not can_track_session_state(ref):
            return

    def mark_processed(
        outcome: Literal["completed", "skipped", "error"],
        options: dict[str, Any] | None = None,
    ) -> None:
        if not params.get("enabled"):
            return
        ref = resolve_ref(options)

    return {
        "markProcessing": mark_processing,
        "markIdle": mark_idle,
        "markProcessed": mark_processed,
    }


__all__ = ["create_diagnostic_message_lifecycle"]
