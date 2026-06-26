"""Sleep helper that respects abort signal.

Mirrors src/agents/utils/sleep.ts.
"""

from __future__ import annotations

import asyncio
import time


async def sleep(ms: float, event: asyncio.Event | None = None) -> None:
    """Sleep for ms milliseconds, optionally aborting via an asyncio.Event."""
    if event is not None and event.is_set():
        raise asyncio.CancelledError("Aborted")
    if ms <= 0:
        if event is not None and event.is_set():
            raise asyncio.CancelledError("Aborted")
        return
    try:
        if event is not None:
            done, pending = await asyncio.wait(
                {asyncio.create_task(asyncio.sleep(ms / 1000)),
                 asyncio.create_task(event.wait())},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for t in done:
                if t.exception() is not None:
                    raise t.exception()
                # If event.wait() completed first, it was aborted
                if t._coro.__name__ == "wait":
                    raise asyncio.CancelledError("Aborted")
        else:
            await asyncio.sleep(ms / 1000)
    except asyncio.CancelledError:
        raise


def sleep_sync(ms: float) -> None:
    """Synchronous sleep for ms milliseconds."""
    if ms > 0:
        time.sleep(ms / 1000)
