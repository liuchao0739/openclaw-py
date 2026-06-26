"""Timeout wrapper for node-host operations using cancellation.

Mirrors src/node-host/with-timeout.ts. Uses asyncio for cancellation.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


def _resolve_timer_timeout_ms(timeout_ms: Any, min_val: int = 1) -> int | None:
    if isinstance(timeout_ms, bool):
        return None
    if isinstance(timeout_ms, (int, float)):
        if math.isnan(timeout_ms) or math.isinf(timeout_ms):
            return None
        ms = int(timeout_ms)
        return max(min_val, ms) if ms > 0 else None
    return None


async def with_timeout(
    work: Callable[[asyncio.Event | None], Awaitable[T]],
    timeout_ms: Any = None,
    label: str | None = None,
) -> T:
    """Run work with an optional timeout.

    Races work against a timeout task, raises asyncio.TimeoutError on timeout.
    """
    resolved = _resolve_timer_timeout_ms(timeout_ms) if timeout_ms is not None else None
    if resolved is None:
        return await work(None)
    timeout_seconds = resolved / 1000.0
    cancel_event = asyncio.Event()

    async def _timeout_task() -> None:
        await asyncio.sleep(timeout_seconds)
        cancel_event.set()

    timeout_task = asyncio.create_task(_timeout_task())
    try:
        work_task = asyncio.create_task(work(cancel_event))
        done, pending = await asyncio.wait(
            {work_task, timeout_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if timeout_task in done:
            raise asyncio.TimeoutError(f"{label or 'request'} timed out")
        return work_task.result()
    finally:
        timeout_task.cancel()
        try:
            await timeout_task
        except (asyncio.CancelledError, Exception):
            pass
