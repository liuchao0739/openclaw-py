"""Channel bot-pair loop guard shared by turn adapters."""

from __future__ import annotations

import time
from typing import Any


class _PairLoopGuard:
    """Process-local guard for detecting repeated bot-to-bot reply loops."""

    def __init__(self, prune_interval_ms: int = 60_000) -> None:
        self._prune_interval_ms = prune_interval_ms
        self._entries: dict[str, dict[str, Any]] = {}
        self._last_prune = 0

    def record_and_check(
        self,
        scope_id: str,
        conversation_id: str,
        sender_id: str,
        receiver_id: str,
        settings: dict[str, Any] | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        """Record a bot pair interaction and check if it should be suppressed."""
        now = now_ms or int(time.time() * 1000)
        self._prune(now)

        key = f"{scope_id}:{conversation_id}:{sender_id}:{receiver_id}"
        entry = self._entries.get(key, {"count": 0, "firstAt": now})

        max_count = 3
        window_ms = 30_000
        if settings:
            max_count = settings.get("maxInteractions", max_count)
            window_ms = settings.get("windowMs", window_ms)

        # Reset if outside window
        if now - entry["firstAt"] > window_ms:
            entry = {"count": 0, "firstAt": now}

        entry["count"] += 1
        self._entries[key] = entry

        suppressed = entry["count"] > max_count
        return {
            "suppressed": suppressed,
            "count": entry["count"],
            "maxCount": max_count,
            "windowMs": window_ms,
        }

    def clear(self) -> None:
        self._entries.clear()

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._entries.values())

    def _prune(self, now: int) -> None:
        if now - self._last_prune < self._prune_interval_ms:
            return
        self._last_prune = now
        cutoff = now - 300_000  # 5 min
        self._entries = {k: v for k, v in self._entries.items() if v.get("firstAt", 0) > cutoff}


_channel_bot_pair_loop_guard = _PairLoopGuard(prune_interval_ms=60_000)


def record_channel_bot_pair_loop_and_check_suppression(
    scope_id: str,
    conversation_id: str,
    sender_id: str,
    receiver_id: str,
    config: dict[str, Any] | None = None,
    defaults_config: dict[str, Any] | None = None,
    default_enabled: bool = True,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Record a bot pair interaction and return whether the loop guard should suppress it."""
    settings = config or defaults_config or {}
    if not default_enabled and not config:
        return {"suppressed": False, "count": 0, "maxCount": 0, "windowMs": 0}

    return _channel_bot_pair_loop_guard.record_and_check(
        scope_id, conversation_id, sender_id, receiver_id, settings, now_ms,
    )


def clear_channel_bot_pair_loop_guard_for_tests() -> None:
    """Clear channel bot-loop state for isolated tests."""
    _channel_bot_pair_loop_guard.clear()


def list_tracked_channel_bot_pairs_for_tests() -> list[dict[str, Any]]:
    """List tracked bot-loop pairs for isolated tests."""
    return _channel_bot_pair_loop_guard.snapshot()
