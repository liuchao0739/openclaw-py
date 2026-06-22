"""Serialize async work per key (ported from plugin-sdk keyed-async-queue)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class KeyedAsyncQueue:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def enqueue(self, key: str, task: Callable[[], Awaitable[T]]) -> T:
        async with self._locks[key]:
            return await task()