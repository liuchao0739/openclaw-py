"""ACPX turn adapters for lazy and legacy ACP runtimes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol


class AcpRuntimeHandle(Protocol):
    session_key: str
    backend: str
    runtime_session_name: str


class AcpRuntimeTurnInput(Protocol):
    handle: AcpRuntimeHandle
    text: str
    mode: str
    request_id: str


class AcpRuntime(Protocol):
    async def ensure_session(self, input: Any) -> Any: ...

    def start_turn(self, input: AcpRuntimeTurnInput) -> dict[str, Any]: ...

    def run_turn(self, input: AcpRuntimeTurnInput) -> AsyncIterator[Any]: ...

    async def cancel(self, input: Any) -> None: ...

    async def close(self, input: Any) -> None: ...


class _LegacyRunTurnEventQueue:
    def __init__(self) -> None:
        self._items: list[Any] = []
        self._waits: list[asyncio.Future[Any | None]] = []
        self._closed = False
        self._error: BaseException | None = None

    def push(self, item: Any) -> None:
        if self._closed:
            return
        if self._waits:
            waiter = self._waits.pop(0)
            if not waiter.done():
                waiter.set_result(item)
            return
        self._items.append(item)

    def clear(self) -> None:
        self._items.clear()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for waiter in self._waits:
            if not waiter.done():
                waiter.set_result(None)
        self._waits.clear()

    def fail(self, error: BaseException) -> None:
        if self._closed:
            return
        self._error = error
        self._closed = True
        for waiter in self._waits:
            if not waiter.done():
                waiter.set_exception(error)
        self._waits.clear()

    async def _next(self) -> Any | None:
        if self._items:
            return self._items.pop(0)
        if self._error is not None:
            raise self._error
        if self._closed:
            return None
        loop = asyncio.get_running_loop()
        waiter: asyncio.Future[Any | None] = loop.create_future()
        self._waits.append(waiter)
        return await waiter

    async def iterate(self) -> AsyncIterator[Any]:
        while True:
            item = await self._next()
            if item is None:
                return
            yield item


def _read_turn_field(input: Any, snake: str, camel: str) -> Any:
    if isinstance(input, dict):
        return input.get(camel, input.get(snake))
    return getattr(input, snake, getattr(input, camel, None))


def _legacy_run_turn_as_start_turn(
    runtime: AcpRuntime,
    input: Any,
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    result: asyncio.Future[Any] = loop.create_future()
    queue = _LegacyRunTurnEventQueue()
    result_settled = False

    def settle_result(next_result: dict[str, Any]) -> None:
        nonlocal result_settled
        if result_settled:
            return
        result_settled = True
        if not result.done():
            result.set_result(next_result)

    async def _run() -> None:
        try:
            async for event in runtime.run_turn(input):
                if isinstance(event, dict) and event.get("type") == "done":
                    settle_result(
                        {
                            "status": "completed",
                            **(
                                {"stopReason": event["stopReason"]}
                                if event.get("stopReason")
                                else {}
                            ),
                        }
                    )
                    continue
                if isinstance(event, dict) and event.get("type") == "error":
                    settle_result(
                        {
                            "status": "failed",
                            "error": {
                                "message": event.get("message"),
                                **({"code": event["code"]} if event.get("code") else {}),
                                **(
                                    {"detailCode": event["detailCode"]}
                                    if event.get("detailCode")
                                    else {}
                                ),
                                **(
                                    {"retryable": event["retryable"]}
                                    if "retryable" in event
                                    else {}
                                ),
                            },
                        }
                    )
                    continue
                queue.push(event)
            settle_result(
                {
                    "status": "failed",
                    "error": {
                        "code": "ACP_TURN_FAILED",
                        "message": "ACP turn ended without a terminal done event.",
                    },
                }
            )
        except Exception as error:  # noqa: BLE001
            if not result.done():
                result.set_exception(error)
            queue.fail(error if isinstance(error, BaseException) else RuntimeError(str(error)))
            return
        queue.close()

    task = asyncio.create_task(_run())

    async def _events() -> AsyncIterator[Any]:
        try:
            async for item in queue.iterate():
                yield item
        finally:
            if not task.done():
                task.cancel()

    async def _cancel(input_args: dict[str, Any] | None = None) -> None:
        handle = _read_turn_field(input, "handle", "handle")
        await runtime.cancel(
            {"handle": handle, "reason": (input_args or {}).get("reason")}
        )

    async def _close_stream(_input_args: dict[str, Any] | None = None) -> None:
        queue.clear()
        queue.close()

    return {
        "requestId": _read_turn_field(input, "request_id", "requestId"),
        "events": _events(),
        "result": result,
        "cancel": _cancel,
        "closeStream": _close_stream,
    }


def start_runtime_turn(runtime: AcpRuntime, input: Any) -> dict[str, Any]:
    start_turn = getattr(runtime, "start_turn", None)
    if callable(start_turn):
        return start_turn(input)
    return _legacy_run_turn_as_start_turn(runtime, input)


async def _resolve_turn(
    resolve_runtime: Callable[[], Awaitable[AcpRuntime]],
    input: Any,
) -> dict[str, Any]:
    runtime = await resolve_runtime()
    return start_runtime_turn(runtime, input)


def lazy_start_runtime_turn(
    resolve_runtime: Callable[[], Awaitable[AcpRuntime]],
    input: Any,
) -> dict[str, Any]:
    turn_promise = asyncio.ensure_future(_resolve_turn(resolve_runtime, input))

    async def _events() -> AsyncIterator[Any]:
        turn = await turn_promise
        async for event in turn["events"]:
            yield event

    async def _result() -> Any:
        turn = await turn_promise
        return await turn["result"]

    async def _cancel(input_args: dict[str, Any] | None = None) -> None:
        turn = await turn_promise
        await turn["cancel"](input_args)

    async def _close_stream(input_args: dict[str, Any] | None = None) -> None:
        turn = await turn_promise
        await turn["closeStream"](input_args)

    return {
        "requestId": _read_turn_field(input, "request_id", "requestId"),
        "events": _events(),
        "result": _result(),
        "cancel": _cancel,
        "closeStream": _close_stream,
    }
