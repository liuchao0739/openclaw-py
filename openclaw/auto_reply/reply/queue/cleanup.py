"""Queue cleanup — remove stale entries and prune expired queues."""

from __future__ import annotations

import time
from typing import Any

from openclaw.auto_reply.reply.queue.state import get_queue_state

STALE_QUEUE_TIMEOUT_MS = 30 * 60 * 1000  # 30 minutes


def prune_stale_queues(
    *,
    now_ms: int | None = None,
    max_age_ms: int = STALE_QUEUE_TIMEOUT_MS,
) -> int:
    """Prune queues that have been stale for longer than max_age_ms.

    Returns the number of pruned sessions.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    state = get_queue_state()
    pruned = 0

    for session_key in list(state._queues.keys()):
        queue = state._queues[session_key]
        if not queue:
            state._queues.pop(session_key, None)
            pruned += 1
            continue

        # Check if the oldest entry is stale
        oldest = queue[0]
        enqueued_at = oldest.get("enqueuedAt", 0)
        if enqueued_at and (now_ms - enqueued_at) > max_age_ms:
            state._queues.pop(session_key, None)
            state._active_run.pop(session_key, None)
            pruned += 1

    return pruned


def clear_all_queues() -> int:
    """Clear all queues. Returns the number of cleared sessions."""
    state = get_queue_state()
    count = len(state._queues)
    state.clear_all()
    return count


def get_queue_stats() -> dict[str, Any]:
    """Get queue statistics for diagnostics."""
    state = get_queue_state()
    total_pending = sum(len(q) for q in state._queues.values())
    active_sessions = sum(1 for v in state._active_run.values() if v is not None)
    return {
        "totalSessions": len(state._queues),
        "totalPending": total_pending,
        "activeRuns": active_sessions,
    }
