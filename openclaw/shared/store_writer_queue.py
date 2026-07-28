"""Store writer queue serializes file writes within one process."""

from __future__ import annotations

import asyncio
from typing import Any, Callable


def _is_active_store_writer(queues: dict[str, dict[str, Any]], store_path: str) -> bool:
    return False


async def _drain_store_writer_queue(
    queues: dict[str, dict[str, Any]],
    store_path: str,
) -> None:
    queue = queues.get(store_path)
    if queue is None:
        return
    if queue.get("drainPromise"):
        await queue["drainPromise"]
        return

    async def _do_drain() -> None:
        try:
            while queue["pending"]:
                task = queue["pending"].pop(0)
                try:
                    result = await task["fn"]()
                    task["resolve"](result)
                except Exception as err:
                    task["reject"](err)
        finally:
            queue["running"] = False
            queue["drainPromise"] = None
            if queue["pending"]:
                asyncio.get_event_loop().create_task(_drain_store_writer_queue(queues, store_path))
            else:
                queues.pop(store_path, None)

    queue["running"] = True
    queue["drainPromise"] = asyncio.get_event_loop().create_task(_do_drain())
    await queue["drainPromise"]


async def run_queued_store_write(
    queues: dict[str, dict[str, Any]],
    store_path: str,
    fn: Callable[[], Any],
    reentrant: bool = False,
) -> Any:
    if not store_path or not isinstance(store_path, str):
        raise ValueError(f"storePath must be a non-empty string, got {repr(store_path)}")
    queue = queues.setdefault(store_path, {"running": False, "pending": [], "drainPromise": None})

    loop = asyncio.get_event_loop()
    future = loop.create_future()

    task = {
        "fn": fn,
        "resolve": future.set_result,
        "reject": future.set_exception,
    }
    queue["pending"].append(task)
    loop.create_task(_drain_store_writer_queue(queues, store_path))
    return await future


def clear_store_writer_queues_for_test(queues: dict[str, dict[str, Any]], message: str) -> None:
    for queue in queues.values():
        for task in queue.get("pending", []):
            task["reject"](Exception(message))
    queues.clear()
