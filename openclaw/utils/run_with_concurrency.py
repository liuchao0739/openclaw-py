from __future__ import annotations

import asyncio
from typing import Any, Literal


async def run_tasks_with_concurrency(params: dict) -> dict:
    tasks = params["tasks"]
    limit = params["limit"]
    on_task_error = params.get("onTaskError")
    error_mode = params.get("errorMode", "continue")
    if not tasks:
        return {"results": [], "firstError": None, "hasError": False}

    resolved_limit = max(1, min(limit, len(tasks)))
    results: list[Any] = [None] * len(tasks)
    next_index = 0
    state: dict[str, Any] = {"firstError": None, "hasError": False}

    async def worker() -> None:
        nonlocal next_index
        while True:
            if error_mode == "stop" and state["hasError"]:
                return
            index = next_index
            next_index += 1
            if index >= len(tasks):
                return
            try:
                results[index] = await tasks[index]()
            except Exception as error:
                if not state["hasError"]:
                    state["firstError"] = error
                    state["hasError"] = True
                if on_task_error:
                    on_task_error(error, index)
                if error_mode == "stop":
                    return

    workers = [worker() for _ in range(resolved_limit)]
    await asyncio.gather(*workers, return_exceptions=True)
    return {"results": results, "firstError": state["firstError"], "hasError": state["hasError"]}
