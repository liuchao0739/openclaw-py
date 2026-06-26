"""Gateway-client event-loop readiness primitive.

Mirrors src/gateway/event-loop-ready.ts (barrel re-export). Stub implementation.
"""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict


class EventLoopReadyOptions(TypedDict, total=False):
    timeout_ms: int
    poll_interval_ms: int


class EventLoopReadyResult(TypedDict):
    ready: bool
    elapsed_ms: int


async def wait_for_event_loop_ready(
    opts: EventLoopReadyOptions | None = None,
) -> EventLoopReadyResult:
    """Wait for the event loop to be ready (stub — returns immediately)."""
    return {"ready": True, "elapsed_ms": 0}
