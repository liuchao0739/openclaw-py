"""Lazy promise loader for manual-control promise caching."""

from __future__ import annotations

import asyncio
from typing import Any, Callable


def create_lazy_promise_loader(
    load: Callable[[], Any],
    cache_rejections: bool = False,
) -> dict[str, Any]:
    promise: asyncio.Future | None = None

    def _create_promise() -> asyncio.Future:
        loop = asyncio.get_event_loop()
        future = loop.create_task(_do_load())
        if not cache_rejections:
            def _on_done(fut: asyncio.Future) -> None:
                nonlocal promise
                if promise is fut:
                    promise = None
            future.add_done_callback(_on_done)
        return future

    async def _do_load() -> Any:
        result = load()
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _load() -> Any:
        nonlocal promise
        if promise is None:
            promise = _create_promise()
        return await promise

    def _clear() -> None:
        nonlocal promise
        promise = None

    return {"load": _load, "clear": _clear}


def create_lazy_import_loader(
    load: Callable[[], Any],
    cache_rejections: bool = False,
) -> dict[str, Any]:
    return create_lazy_promise_loader(load, cache_rejections)
