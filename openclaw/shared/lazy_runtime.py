"""Lazy runtime helpers for dynamic imports through cached runtime surfaces."""

from __future__ import annotations

import asyncio
from typing import Any, Callable


def create_lazy_runtime_surface(
    importer: Callable[[], Any],
    select: Callable[[Any], Any],
) -> Callable[[], Any]:
    cached: asyncio.Future | None = None

    async def _load() -> Any:
        nonlocal cached
        if cached is None:
            loop = asyncio.get_event_loop()
            raw = importer()
            if asyncio.iscoroutine(raw):
                module = await raw
            else:
                module = raw
            cached = loop.create_task(asyncio.sleep(0, result=select(module)))
        return await cached

    return _load


def create_lazy_runtime_module(
    importer: Callable[[], Any],
) -> Callable[[], Any]:
    return create_lazy_runtime_surface(importer, lambda m: m)


def create_lazy_runtime_named_export(
    importer: Callable[[], Any],
    key: str,
) -> Callable[[], Any]:
    return create_lazy_runtime_surface(importer, lambda m: m[key])


def create_lazy_runtime_method(
    load: Callable[[], Any],
    select: Callable[[Any], Any],
) -> Callable[..., Any]:
    async def _invoke(*args: Any) -> Any:
        surface = await load()
        method = select(surface)
        result = method(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    return _invoke


def create_lazy_runtime_method_binder(
    load: Callable[[], Any],
) -> Callable[[Callable[[Any], Any]], Callable[..., Any]]:
    def _bind(select: Callable[[Any], Any]) -> Callable[..., Any]:
        return create_lazy_runtime_method(load, select)
    return _bind
