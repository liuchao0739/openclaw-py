"""Skill serialization helpers compact skill metadata and coordinate sync queue updates.

Mirrors src/skills/loading/serialize.ts.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")

_SKILLS_SYNC_QUEUE: dict[str, asyncio.Future] = {}


async def serialize_by_key(key: str, task: Callable[[], Awaitable[T]]) -> T:
    """Serialize async work by key so repeated skill loads do not race on shared files."""
    prev = _SKILLS_SYNC_QUEUE.get(key)
    if prev is not None:
        try:
            await prev
        except Exception:
            pass

    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    _SKILLS_SYNC_QUEUE[key] = future

    try:
        result = await task()
        future.set_result(result)
        return result
    except Exception as exc:
        future.set_exception(exc)
        raise
    finally:
        if _SKILLS_SYNC_QUEUE.get(key) is future:
            del _SKILLS_SYNC_QUEUE[key]
