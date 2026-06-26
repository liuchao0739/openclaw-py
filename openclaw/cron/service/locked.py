"""Process-local cron operation serialization by store path.

Mirrors src/cron/service/locked.ts. Serializes cron operations per store path
while preserving state-local operation ordering.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


def _resolve_chain(awaitable: Awaitable[Any]) -> asyncio.Future:
    """Return a future that settles (to None) after ``awaitable`` settles."""
    fut: asyncio.Future = asyncio.get_event_loop().create_future()

    def _done(res: Any) -> None:
        if not fut.done():
            fut.set_result(None)

    def _err(exc: Any) -> None:
        if not fut.done():
            fut.set_result(None)  # swallow errors, resolve to None

    asyncio.ensure_future(awaitable).add_done_callback(
        lambda t: _done(t.result()) if not t.exception() else _err(t.exception())
    )
    return fut


async def locked(
    state: Any,
    fn: Callable[[], Awaitable[Any]],
    *,
    _store_locks: dict[str, asyncio.Future] | None = None,
) -> Any:
    """Serialize cron operations per store path.

    ``state`` must have ``deps.store_path`` and ``op`` (an asyncio.Future or None)
    attributes. ``_store_locks`` is injected for testing.
    """
    store_locks: dict[str, asyncio.Future] = _store_locks if _store_locks is not None else _GLOBAL_STORE_LOCKS
    store_path = state.deps.store_path
    store_op = store_locks.get(store_path)
    state_op = getattr(state, "op", None)

    async def _noop():
        pass

    async def _run():
        # Wait for both the state-local op and the store-level op to settle.
        if state_op is not None:
            try:
                await asyncio.shield(state_op)
            except Exception:
                pass
        if store_op is not None:
            try:
                await asyncio.shield(store_op)
            except Exception:
                pass
        return await fn()

    next_future = asyncio.ensure_future(_run())

    async def _keep_alive():
        try:
            await next_future
        except Exception:
            pass

    keep_alive = asyncio.ensure_future(_keep_alive())
    state.op = keep_alive
    store_locks[store_path] = keep_alive
    return await next_future


_GLOBAL_STORE_LOCKS: dict[str, asyncio.Future] = {}


def _reset_store_locks_for_tests() -> None:
    _GLOBAL_STORE_LOCKS.clear()
