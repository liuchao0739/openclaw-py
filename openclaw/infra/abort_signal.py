from __future__ import annotations

import asyncio
import time
from typing import Any, Callable


async def sleep_with_abort(
    duration_ms: int,
    abort_signal: Any | None = None,
) -> None:
    if abort_signal is not None and getattr(abort_signal, "aborted", False):
        raise asyncio.CancelledError("Aborted before sleep")

    loop = asyncio.get_event_loop()
    end_time = loop.time() + duration_ms / 1000.0

    while True:
        if abort_signal is not None and getattr(abort_signal, "aborted", False):
            raise asyncio.CancelledError("Aborted during sleep")

        remaining = end_time - loop.time()
        if remaining <= 0:
            break

        sleep_chunk = min(remaining, 0.1)
        try:
            await asyncio.sleep(sleep_chunk)
        except asyncio.CancelledError:
            if abort_signal is not None and getattr(abort_signal, "aborted", False):
                raise
            raise


def compute_backoff(
    attempt: int,
    *,
    min_delay_ms: int = 100,
    max_delay_ms: int = 30000,
    factor: float = 2.0,
    jitter: float = 0.1,
) -> int:
    import random

    delay = min_delay_ms * (factor ** attempt)
    delay = min(delay, max_delay_ms)

    if jitter > 0:
        jitter_amount = delay * jitter
        delay = delay - jitter_amount + (random.random() * jitter_amount * 2)

    return max(int(delay), 0)


class AbortSignal:
    def __init__(self):
        self.aborted = False
        self._reason: str | None = None
        self._callbacks: list[Callable] = []

    def abort(self, reason: str | None = None) -> None:
        self.aborted = True
        self._reason = reason
        for cb in self._callbacks:
            try:
                cb(reason)
            except Exception:
                pass

    def on_abort(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def clear(self) -> None:
        self.aborted = False
        self._reason = None
        self._callbacks.clear()

    @property
    def reason(self) -> str | None:
        return self._reason


class AbortController:
    def __init__(self):
        self.signal = AbortSignal()

    def abort(self, reason: str | None = None) -> None:
        self.signal.abort(reason)

    def clear(self) -> None:
        self.signal.clear()
