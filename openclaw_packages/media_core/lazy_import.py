from __future__ import annotations

import asyncio
import threading
from typing import Any, Awaitable, Callable, Generic, TypeVar

_T = TypeVar("_T")

_LazyLoader = Callable[[], Awaitable[_T]]


class LazyPromiseLoader(Generic[_T]):
    def __init__(self, load: _LazyLoader[_T], cache_rejections: bool = False) -> None:
        self._load = load
        self._cache_rejections = cache_rejections
        self._lock = threading.Lock()
        self._future: asyncio.Future[_T] | None = None

    async def load(self) -> _T:
        import asyncio

        if self._future is None:
            with self._lock:
                if self._future is None:
                    self._future = asyncio.ensure_future(self._load())
                    if not self._cache_rejections:
                        def _on_done(fut: asyncio.Future[_T]) -> None:
                            if fut is self._future and fut.cancelled():
                                self._future = None
                            elif fut.exception() is not None:
                                if fut is self._future:
                                    self._future = None

                        self._future.add_done_callback(_on_done)
        return await self._future

    def clear(self) -> None:
        with self._lock:
            if self._future is not None and not self._future.done():
                self._future.cancel()
            self._future = None


def create_lazy_import_loader(
    load: _LazyLoader[_T],
    cache_rejections: bool = False,
) -> LazyPromiseLoader[_T]:
    return LazyPromiseLoader(load=load, cache_rejections=cache_rejections)
