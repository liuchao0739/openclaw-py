"""Queue draining — process queued follow-up replies."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from openclaw.auto_reply.reply.queue.enqueue import dequeue_followup, peek_followup
from openclaw.auto_reply.reply.queue.settings import resolve_queue_settings
from openclaw.auto_reply.reply.queue.state import get_queue_state
from openclaw.auto_reply.reply.queue.types import FollowupRun


async def drain_queue(
    session_key: str,
    handler: Any,
    *,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Drain all queued follow-ups for a session, calling handler for each.

    Returns a list of handler results.
    """
    settings = resolve_queue_settings(config)
    debounce_ms = settings.get("debounceMs", 500)

    results: list[dict[str, Any]] = []

    while True:
        run = dequeue_followup(session_key)
        if run is None:
            break

        try:
            result = await handler(run)
            results.append({"run": run, "result": result, "error": None})
        except Exception as err:
            results.append({"run": run, "result": None, "error": str(err)})

        # Debounce between runs
        if debounce_ms > 0:
            await asyncio.sleep(debounce_ms / 1000.0)

    return results


async def drain_single(
    session_key: str,
    handler: Any,
) -> dict[str, Any] | None:
    """Drain a single queued follow-up for a session.

    Returns the handler result dict, or None if the queue was empty.
    """
    run = dequeue_followup(session_key)
    if run is None:
        return None

    try:
        result = await handler(run)
        return {"run": run, "result": result, "error": None}
    except Exception as err:
        return {"run": run, "result": None, "error": str(err)}


def has_queued_followups(session_key: str) -> bool:
    """Check if a session has queued follow-ups."""
    state = get_queue_state()
    return state.has_pending(session_key)
