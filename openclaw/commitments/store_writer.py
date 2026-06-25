"""Per-store-path mutation gate for the commitments store.

Uses an in-process queue + file-lock pattern for exclusive writes.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable

_WRITER_QUEUES: dict[str, asyncio.Lock] = {}


async def run_exclusive_commitments_store_write(
    store_path: str,
    fn: Callable[[], Any],
) -> Any:
    """Run an exclusive store write with file locking and queueing."""
    # Ensure parent directory exists
    parent = os.path.dirname(store_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Get or create a per-path lock
    if store_path not in _WRITER_QUEUES:
        _WRITER_QUEUES[store_path] = asyncio.Lock()

    async with _WRITER_QUEUES[store_path]:
        # File lock (deferred to plugin-sdk/file-lock; uses in-process lock as fallback)
        try:
            from openclaw.plugin_sdk.file_lock import with_file_lock

            return await with_file_lock(store_path, fn)
        except Exception:
            # Fallback: just run the function with the in-process lock
            result = fn()
            if hasattr(result, "__await__"):
                return await result
            return result
