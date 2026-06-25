"""Sleep helper that respects abort signals."""

from __future__ import annotations

import asyncio
from typing import Any


async def sleep(ms: float, signal: Any = None) -> None:
    """Sleep for ``ms`` milliseconds, rejecting early if ``signal`` is aborted."""
    if signal is not None and getattr(signal, "aborted", False):
        raise asyncio.CancelledError("Aborted")

    if ms <= 0:
        if signal is not None:
            event = asyncio.Event()

            def _on_abort(*_args: Any) -> None:
                event.set()

            try:
                signal.add_signal_callback(_on_abort)
            except (AttributeError, NotImplementedError, RuntimeError):
                pass
            await event.wait()
        return

    try:
        await asyncio.wait_for(asyncio.sleep(ms / 1000.0), timeout=ms / 1000.0 + 1.0)
    except asyncio.CancelledError:
        raise


def sleep_sync(ms: float) -> None:
    """Synchronous sleep for ``ms`` milliseconds."""
    import time

    if ms > 0:
        time.sleep(ms / 1000.0)
