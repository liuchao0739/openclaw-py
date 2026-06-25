"""Queue enqueue logic for follow-up replies."""

from __future__ import annotations

import time
from typing import Any

from openclaw.auto_reply.reply.queue.normalize import (
    apply_drop_policy,
    dedupe_queue,
    normalize_followup_run,
)
from openclaw.auto_reply.reply.queue.settings import resolve_queue_settings
from openclaw.auto_reply.reply.queue.state import get_queue_state
from openclaw.auto_reply.reply.queue.types import FollowupRun, QueueSettings


def enqueue_followup(
    session_key: str,
    run: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
    settings: QueueSettings | None = None,
) -> list[FollowupRun]:
    """Enqueue a follow-up run for a session.

    Returns the updated queue.
    """
    if settings is None:
        settings = resolve_queue_settings(config)

    state = get_queue_state()
    queue = state.get_queue(session_key)

    normalized = normalize_followup_run(run)
    queue = [*queue, normalized]

    # Apply dedupe
    dedupe_mode = "message-id"
    queue = dedupe_queue(queue, dedupe_mode)

    # Apply cap with drop policy
    cap = settings.get("cap", 10)
    drop_policy = settings.get("dropPolicy", "old")
    queue = apply_drop_policy(queue, cap, drop_policy)

    state.set_queue(session_key, queue)
    return queue


def dequeue_followup(session_key: str) -> FollowupRun | None:
    """Dequeue the next follow-up run for a session.

    Returns None if the queue is empty.
    """
    state = get_queue_state()
    queue = state.get_queue(session_key)
    if not queue:
        return None
    next_run = queue[0]
    state.set_queue(session_key, queue[1:])
    return next_run


def peek_followup(session_key: str) -> FollowupRun | None:
    """Peek at the next follow-up run without removing it."""
    state = get_queue_state()
    queue = state.get_queue(session_key)
    return queue[0] if queue else None


def clear_session_queue(session_key: str) -> list[FollowupRun]:
    """Clear all queued follow-ups for a session."""
    state = get_queue_state()
    return state.clear_queue(session_key)
