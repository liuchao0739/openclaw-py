"""Per-file mutation queue.

Serializes edits/writes targeting the same real file while allowing independent
files to mutate in parallel.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

_file_mutation_queues: dict[str, asyncio.Future[None]] = {}


def _get_mutation_queue_key(file_path: str) -> str:
    resolved = os.path.realpath(file_path)
    if os.path.exists(resolved):
        return resolved
    return os.path.abspath(resolved)


async def with_file_mutation_queue(file_path: str, fn: Any) -> Any:
    """Serialize file mutation operations targeting the same file."""
    key = _get_mutation_queue_key(file_path)
    current_queue = _file_mutation_queues.get(key)

    next_future: asyncio.Future[None] = asyncio.get_event_loop().create_future()
    _file_mutation_queues[key] = next_future

    if current_queue is not None:
        await current_queue

    try:
        return await fn()
    finally:
        next_future.set_result(None)
        if _file_mutation_queues.get(key) is next_future:
            _file_mutation_queues.pop(key, None)
