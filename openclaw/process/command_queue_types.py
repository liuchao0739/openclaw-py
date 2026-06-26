"""Public enqueue knobs shared by command-lane callers and narrower injection points.

Mirrors src/process/command-queue.types.ts.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypedDict


class CommandQueueEnqueueOptions(TypedDict, total=False):
    warnAfterMs: int
    onWait: Callable[[int, int], None]
    taskTimeoutMs: int
    taskTimeoutProgressAtMs: Callable[[], int | None]
    taskTimeoutAbortSignal: Any
    taskTimeoutAbortGraceMs: int
    taskTimeoutReleaseSignal: Any
    priority: str  # "foreground" | "normal" | "background"


CommandQueueEnqueueFn = Callable[..., Awaitable[Any]]
